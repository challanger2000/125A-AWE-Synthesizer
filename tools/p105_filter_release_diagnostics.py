"""P105 original AWE64 Gold CT4390: isolated filter and release diagnostics.

Use the hash-pinned SoundFont Spec Test v3.0 with the same P97 gain/latency
and unmodified original MIDI. Avoid the spoken test announcements: select
clean filter test notes after their respective announcement note-offs.

The 50-400 Hz / 400-1500 Hz / 1.5-5 kHz / 5-10 kHz relative ratios are
reported per note, not interpreted as a direct EMU8000 filter impulse
response. No output level, EQ or timing is fitted per note.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, welch

from p98_effect_subtests import load_events


RATE = 48000
FILTER_BANDS = ((80, 400), (400, 1500), (1500, 5000), (5000, 10000))
NOTE_SETS = (
    ("09_filter_cutoff", 39, 55, 65.5, 36),
    ("10_filter_resonance", 63, 71, 77.5, 60),
)


def power_db(a, b):
    return float(10 * np.log10(max(a, 1e-16) / max(b, 1e-16)))


def rms(a):
    return float(np.sqrt(np.mean(np.square(a, dtype=np.float64))))


def verify_midi(events, notes, test, first, origin):
    for note in notes:
        t = first + 0.5 * (note - origin)
        ons = [e for e in events if e["type"] == "note_on" and e["ch"] == 4
               and e["note"] == note and e["v"] == 127
               and abs(e["t"] - t) < 0.005]
        if len(ons) != 1:
            raise ValueError("P105 MIDI filter note mismatch " + test + "/" + str(note))
        offs = [e for e in events if e["ch"] == 4 and e["note"] == note
                and 0 < e["t"] - t < 0.49
                and (e["type"] == "note_off"
                     or (e["type"] == "note_on" and e["v"] == 0))]
        if len(offs) != 1:
            raise ValueError("P105 MIDI filter NoteOff mismatch " + test + "/" + str(note))


def check_note_hardware(reference, native, start):
    # A recorded note is ~422 ms; wait for onset and stop before release.
    a = int(round((start + .08) * RATE))
    b = int(round((start + .32) * RATE))
    rh = reference[a:b].mean(axis=1)
    rn = native[a:b].mean(axis=1)
    if len(rh) < 4096:
        raise ValueError("P105 insufficient note frames")
    nperseg = 4096
    f, ph = welch(rh, RATE, nperseg=nperseg, detrend="constant")
    _, pn = welch(rn, RATE, nperseg=nperseg, detrend="constant")
    bands = []
    for lo, hi in FILTER_BANDS:
        sel = (f >= lo) & (f < hi)
        a = float(ph[sel].sum())
        b = float(pn[sel].sum())
        bands.append({
            "band_hz": "{}-{}".format(lo, hi),
            "reference_power": round(a, 12),
            "native_power": round(b, 12),
            "native_minus_hardware_db": round(power_db(b, a), 3),
            "hardware_weak": a < 1e-11,
        })
    return {
        "hardware_mid_rms": round(rms(rh), 8),
        "native_mid_rms": round(rms(rn), 8),
        "native_minus_hardware_total_db": round(
            20 * np.log10(max(rms(rn), 1e-12) / max(rms(rh), 1e-12)), 3),
        "bands": bands,
    }


def release_curve(audio, off):
    # 20ms envelope windows 20..540ms after a clean NoteOff.
    data = []
    for k in range(1, 27):
        t = off + .02 * k
        a, b = int(t * RATE), int((t + .02) * RATE)
        data.append(rms(audio[a:b].mean(axis=1)))
    return np.asarray(data)


def release_fit(curve):
    # Fit slope relative to the curve at its own onset. This rejects
    # per-note normalization and checks change per second, not loudness.
    times = np.arange(1, 27) * .02 + .01
    dbs = 20 * np.log10(np.maximum(curve, 1e-9))
    valid = (curve > .0004) & (times >= .05) & (times < .40)
    if int(valid.sum()) < 6:
        return {"valid_bins": int(valid.sum()), "slope_db_per_s": None}
    slope = float(np.polyfit(times[valid], dbs[valid], 1)[0])
    return {
        "valid_bins": int(valid.sum()),
        "slope_db_per_s": round(slope, 3),
        "first_40ms_rms": round(float(np.mean(curve[:2])), 7),
        "last_120ms_rms": round(float(np.mean(curve[20:])), 7),
    }


def main():
    p = argparse.ArgumentParser()
    for arg in ("reference", "native", "events", "p97-report", "out"):
        p.add_argument("--" + arg, required=True)
    a = p.parse_args()
    report = json.loads(Path(a.p97_report).read_text(encoding="utf-8"))
    if report.get("compared_seconds") != 264:
        raise ValueError("P105 needs complete P97 CT4390 comparison")
    events = load_events(a.events)
    for name, lo, hi, first, origin in NOTE_SETS:
        verify_midi(events, range(lo, hi + 1), name, first, origin)

    hw, hr = sf.read(a.reference, frames=90 * RATE,
                     dtype="float32", always_2d=True)
    em, er = sf.read(a.native, frames=90 * 44100,
                     dtype="float32", always_2d=True)
    if (hr, er) != (RATE, 44100):
        raise ValueError("P105 incorrect source sample rates")
    em = resample_poly(em, 160, 147, axis=0)
    lag_frames = round(report["original_hardware_relative_latency_ms"] * RATE / 1000)
    if lag_frames >= 0:
        hw = hw[lag_frames:]
    else:
        em = em[-lag_frames:]
    em *= 10 ** (report["hardware_to_native_global_gain_match_db"] / 20)
    if min(len(hw), len(em)) < 90 * RATE - abs(lag_frames):
        raise ValueError("P105 shortened reference or native waveform")

    filter_data = []
    for name, lo, hi, first, origin in NOTE_SETS:
        notes = []
        for note in range(lo, hi + 1):
            start = first + .5 * (note - origin)
            notes.append({"midi_note": note, "start_s": start,
                          **check_note_hardware(hw, em, start)})
        filter_data.append({"test": name, "notes": notes,
                            "median_absolute_note_level_error_db": round(
                                float(np.median(np.abs([n["native_minus_hardware_total_db"]
                                                        for n in notes]))), 3),
                            "median_note_level_error_db": round(
                                float(np.median([n["native_minus_hardware_total_db"]
                                                 for n in notes])), 3)})

    # P102 verified these exact sustained note-offs; analyze *relative*
    # fall rate from the same note's own pre-release plateau.
    release = []
    for label, note, on, off in (("EG2_amp", 58, 1.5, 6.5),
                                  ("EG1_mod_pitch", 59, 9.5, 14.5)):
        on_events = [e for e in events if e["type"] == "note_on"
                     and e["ch"] == 0 and e["note"] == note
                     and e["v"] > 0 and abs(e["t"] - on) < .005]
        off_events = [e for e in events if e["ch"] == 0
                      and e["note"] == note and abs(e["t"] - off) < .005
                      and (e["type"] == "note_off"
                           or (e["type"] == "note_on" and e["v"] == 0))]
        if len(on_events) != 1 or len(off_events) != 1:
            raise ValueError("P105 invalid original envelope MIDI")
        rh, re = release_curve(hw, off), release_curve(em, off)
        fh, fe = release_fit(rh), release_fit(re)
        release.append({"test": label, "note": note, "note_off_s": off,
                        "physical": fh, "native": fe,
                        "native_minus_hardware_release_slope_db_per_s":
                            round(fe["slope_db_per_s"] - fh["slope_db_per_s"], 3)
                            if fe["slope_db_per_s"] is not None
                            and fh["slope_db_per_s"] is not None else None})

    output = {
        "experiment": "P105 dry-timbre filter note spectra and ADSR release slope",
        "reference": "genuine AWE64 Gold CT4390 RCA v3.0",
        "single_global_P97_gain_db": report["hardware_to_native_global_gain_match_db"],
        "filter_tests": filter_data,
        "release_tests": release,
        "limitations": [
            "Original test 9 and 10 use different preset/note-number values per filter step.",
            "Other effects/voice tails may contaminate the note windows; no filter impulse or saturation measurement.",
            "P97 50ms envelope alignment, not phase accuracy.",
            "EG1 modulation-to-pitch release sound amplitude is NOT a direct filter-envelope measurement.",
            "Stereo analog recording, not digital bitwise hardware parity.",
        ],
    }
    Path(a.out).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    for f in filter_data:
        print("P105 {} median abs note level error {:.3f} dB; signed median {:+.3f} dB".format(
            f["test"],f["median_absolute_note_level_error_db"],
            f["median_note_level_error_db"]))
        for n in f["notes"]:
            strong = [b for b in n["bands"] if not b["hardware_weak"]]
            if not strong:
                print("P105 note {}: hardware energy too weak for reliable spectrum".format(n["midi_note"]))
            else:
                print("P105 note {} @ {:.2f}s: level {:+.3f} dB; band error {}".format(
                    n["midi_note"], n["start_s"], n["native_minus_hardware_total_db"],
                    [b["native_minus_hardware_db"] for b in strong]))
    for r in release:
        print("P105 release {}: physical slope {} dB/s; native {} dB/s; delta {} dB/s".format(
            r["test"],r["physical"]["slope_db_per_s"],
            r["native"]["slope_db_per_s"],
            r["native_minus_hardware_release_slope_db_per_s"]))


if __name__=="__main__":
    main()
