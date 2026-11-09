#!/usr/bin/env python3
"""P195 diagnostic: align the isolated P194 low-band anomalies with the
original MIDI events and their spectrum; do not modify audio or hardware DSP.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from p98_effect_subtests import load_events

RATE = 48000


def note_events(events, start, stop):
    return [{"time_s": round(e["t"], 4), "event": e["type"],
             "channel": e["ch"], "a": e["note"], "b": e["v"]}
            for e in events if start <= e["t"] < stop
            and (e["type"] in ("note_on", "note_off", "program_change")
                 or e["type"] == "control_change"
                 and e["note"] in (0, 7, 10, 11, 64, 91, 93))]


def sounding_midi_notes(events, t):
    active = {}
    for e in events:
        if e["t"] > t:
            break
        if e["type"] == "note_on":
            k = (e["ch"], e["note"])
            if e["v"] > 0:
                active[k] = round(e["t"], 4)
            else:
                active.pop(k, None)
        if e["type"] == "note_off":
            active.pop((e["ch"], e["note"]), None)
        if e["type"] == "control_change" and e["note"] in (120, 123):
            for k in list(active):
                if k[0] == e["ch"]:
                    active.pop(k)
    return [{"channel": k[0], "note": k[1], "note_on_s": v}
            for k, v in sorted(active.items())]


def band_power_and_peaks(stereo):
    mid = stereo.mean(axis=1)
    freq = np.fft.rfftfreq(len(mid), 1.0 / RATE)
    power = np.abs(np.fft.rfft(mid * np.hanning(len(mid)))) ** 2
    ix = (freq >= 50) & (freq < 200)
    inds = np.flatnonzero(ix)
    if not len(inds):
        raise ValueError("Insufficient FFT resolution")
    main = inds[np.argsort(power[inds])[-3:][::-1]]
    return {"band_power": float(power[ix].sum()),
            "strongest_50_200_hz_peaks":
            [{"hz": round(float(freq[i]), 2), "power": float(power[i])}
             for i in main]}


def main():
    p = argparse.ArgumentParser()
    for k in ("reference", "native", "events", "p97-report",
              "p194-report", "out"):
        p.add_argument("--" + k, required=True)
    a = p.parse_args()
    p97 = json.loads(Path(a.p97_report).read_text())
    p194 = json.loads(Path(a.p194_report).read_text())
    events = load_events(a.events)
    if p97["compared_seconds"] != 264 or p194["p97_active_seconds_verified"] != 237:
        raise ValueError("Missing anchored P97/P194 dataset")

    ref, rr = sf.read(a.reference, dtype="float32", always_2d=True)
    orig, sr = sf.read(a.native, dtype="float32", always_2d=True)
    if rr != RATE or sr != 44100 or ref.shape[1] != 2 or orig.shape[1] != 2:
        raise ValueError("Unexpected recording formats")
    emu = resample_poly(orig, 160, 147, axis=0)
    lag = round(p97["original_hardware_relative_latency_ms"] * RATE / 1000.)
    if lag >= 0:
        ref = ref[lag:]
    else:
        emu = emu[-lag:]
    emu = emu * (10 ** (p97["hardware_to_native_global_gain_match_db"] / 20.0))

    seconds = [v["second_start"] for v in p194["seconds_sorted_by_absolute_net_excess"]
               if v["section"] in ("03_keynum_to_decay", "04_keynum_to_hold")]
    seconds = sorted(set(seconds))
    if not set((21, 24, 34, 37, 38)).issubset(seconds):
        raise ValueError("P195 expected P194 outlier seconds missing")

    rows = []
    for sec in seconds:
        f0, f1 = sec * RATE, (sec + 1) * RATE
        hw = band_power_and_peaks(ref[f0:f1])
        native = band_power_and_peaks(emu[f0:f1])
        local = []
        for step in range(10):
            i0 = (sec * 10 + step) * (RATE // 10)
            i1 = i0 + RATE // 10
            rp = band_power_and_peaks(ref[i0:i1])["band_power"]
            ep = band_power_and_peaks(emu[i0:i1])["band_power"]
            local.append({"start_s": round(sec + step / 10.0, 2),
                          "hardware_power": rp, "native_power": ep,
                          "native_minus_hw_db": round(float(10 * np.log10(
                              max(ep, 1e-15) / max(rp, 1e-15))), 2)})
        row = {"second_start": sec, "hardware_fft": hw, "native_fft": native,
               "active_notes_at_midpoint": sounding_midi_notes(events, sec + .5),
               "midi_events_minus_0p5_plus_1p5": note_events(events, sec - .5, sec + 1.5),
               "hundred_ms_bands": local}
        rows.append(row)
        print("P195 t=%ds, MIDI active %s, 50-200 Hz HW %.4g vs native %.4g, "
              "native peak %s Hz" %
              (sec, [(n["channel"], n["note"]) for n in row["active_notes_at_midpoint"]],
               hw["band_power"], native["band_power"],
               native["strongest_50_200_hz_peaks"][0]["hz"]))
    out = {
        "experiment": "P195 isolated key-number hold/decay low-band physical oracle",
        "reference": "Original pinned AWE64 Gold analog capture (not bit-exact)",
        "source": "Original pinned MIDI v3.0 and P193 FX-matched 86Box WAV",
        "selected_seconds": rows,
        "limitations": [
            "Active MIDI notes are MIDI ownership, not evidence that the chip still has a sounding voice.",
            "No register traces from the original AWE64 hardware are available.",
            "One-second FFT peaks are not guaranteed fundamentals; source samples and overlap may contribute.",
            "10Hz resolution 100ms windows are only for temporal localization, not precise pitch.",
            "Analog reference lacks capture alignment markers and S/PDIF."
        ],
    }
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
