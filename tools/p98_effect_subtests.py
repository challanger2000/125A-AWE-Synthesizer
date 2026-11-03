"""P98: split original SoundFont Spec Test v3.0 Hall/Chorus A/B/C by MIDI note.

Independent of engine implementation. P97 gain/alignment is reused; never fit
a gain to each note or effect group. Windows are compared on the existing
analog 48 kHz CT4390 capture, not represented as bit-accurate hardware output.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, welch


def rms(x):
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64))))


def db_ratio(a, b):
    """Amplitude-level difference a/b (dB), preserve small energies."""
    return round(float(20 * np.log10(max(a, 1e-12) / max(b, 1e-12))), 3)


def load_events(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    parsed = []
    for row in rows:
        parsed.append({
            "t": float(row["time_sec"]),
            "type": row["type"],
            "ch": int(row["channel"]),
            "note": int(row["a"]),
            "v": int(row["b"]),
        })
    if not parsed or any(b["t"] < a["t"] for a, b in zip(parsed, parsed[1:])):
        raise ValueError("MIDI event TSV empty or not time sorted")
    return parsed


# Boundaries and expected note-on sequences verified against the SHA-pinned
# public v3.0 MIDI, rather than guessed from the recorded waveform.
# A: instrument generator only; B: CC91/CC93 only; C: combined.
TESTS = (
    ("reverb", "A_instrument", 171.4, 179.0, (82, 83, 84, 85), None,
     (171.5, 173.5, 175.5, 177.5)),
    ("reverb", "B_cc91", 180.9, 189.0, (82, 82, 82, 82), 91,
     (181.0, 183.0, 185.0, 187.0)),
    ("reverb", "C_combined", 190.4, 198.4, (82, 83, 84, 85), 91,
     (190.5, 192.5, 194.5, 196.5)),
    ("chorus", "A_instrument", 200.9, 209.0, (86, 87, 88, 89), None,
     (201.0, 203.0, 205.0, 207.0)),
    ("chorus", "B_cc93", 210.4, 218.5, (86, 86, 86, 86), 93,
     (210.5, 212.5, 214.5, 216.5)),
    ("chorus", "C_combined", 219.9, 228.0, (86, 87, 88, 89), 93,
     (220.0, 222.0, 224.0, 226.0)),
)
EXPECTED_CC = (0, 42, 85, 127)
WINDOWS = (
    ("onset", 0.05, 0.30),
    ("body", 0.35, 1.35),
    ("late", 1.45, 1.75),
)
BANDS = ((50, 200), (200, 500), (500, 2000),
         (2000, 5000), (5000, 10000), (10000, 20000))


def find_subtests(events):
    items = []
    for effect, variant, lo, hi, notes, cc, expected_times in TESTS:
        ons = [e for e in events if e["type"] == "note_on" and e["v"] > 0
               and e["ch"] == 0 and lo <= e["t"] < hi]
        actual_notes = tuple(e["note"] for e in ons)
        if actual_notes != notes or len(ons) != 4:
            raise ValueError(
                "{} {} note onsets do not match original v3.0: {}".format(
                    effect, variant, actual_notes))
        for e, target in zip(ons, expected_times):
            if abs(e["t"] - target) > 0.005:
                raise ValueError("Unexpected timestamp for {} {}: {} vs {}".format(
                    effect, variant, e["t"], target))
        parsed = []
        for i, note in enumerate(ons):
            noteoffs = [e for e in events if e["ch"] == note["ch"]
                        and e["note"] == note["note"] and e["t"] > note["t"]
                        and ((e["type"] == "note_on" and e["v"] == 0)
                             or e["type"] == "note_off")]
            if not noteoffs:
                raise ValueError("Missing MIDI note-off: {} {} #{}".format(
                    effect, variant, i))
            off = noteoffs[0]["t"]
            if not 1.5 < off - note["t"] < 2.1:
                raise ValueError("Unexpected MIDI note duration {} to {}".format(
                    note["t"], off))
            prior_cc = [e for e in events if e["type"] == "control_change"
                        and e["ch"] == note["ch"] and e["note"] == cc
                        and e["t"] <= note["t"]] if cc is not None else []
            cc_value = prior_cc[-1]["v"] if prior_cc else None
            if cc is not None and cc_value != EXPECTED_CC[i]:
                raise ValueError("Unexpected {} {} CC{}: {} != {}".format(
                    effect, variant, cc, cc_value, EXPECTED_CC[i]))
            parsed.append({
                "note": note["note"], "on_s": note["t"], "off_s": off,
                "controller": cc, "controller_value": cc_value,
                "send_fraction": i / 3,
            })
        items.append((effect, variant, parsed))
    return items


def band_delta(x, y, rate):
    """A 1-second stabilized-body mid-channel spectral check, NOT IR parity."""
    # x: reference stereo; y: already level-matched emulator stereo
    fx, pr = welch(x.mean(axis=1), fs=rate, nperseg=4096, axis=0)
    _, pn = welch(y.mean(axis=1), fs=rate, nperseg=4096, axis=0)
    band = []
    for lo, hi in BANDS:
        ix = (fx >= lo) & (fx < hi)
        a = float(pr[ix].sum())
        b = float(pn[ix].sum())
        band.append({
            "band_hz": "{}-{}".format(lo, hi),
            "native_minus_hardware_db": round(
                float(10 * np.log10(max(b, 1e-15) / max(a, 1e-15))), 3),
            "reference_energy_weak": a < 1e-8,
        })
    return band


def measure(ref, native, rate, start, end):
    a = max(0, int(round(start * rate)))
    b = min(len(ref), len(native), int(round(end * rate)))
    if b - a < 256:
        raise ValueError("Invalid/short note window {}..{}".format(start, end))
    x, y = ref[a:b], native[a:b]
    hrms, nrms = rms(x), rms(y)
    mid_hw, side_hw = rms(x.mean(axis=1)), rms((x[:, 0] - x[:, 1]) * 0.5)
    mid_native, side_native = rms(y.mean(axis=1)), rms((y[:, 0] - y[:, 1]) * 0.5)
    return {
        "hardware_rms": round(hrms, 7),
        "native_rms_global_gain_matched": round(nrms, 7),
        "native_minus_hardware_rms_db": db_ratio(nrms, hrms),
        "hardware_side_to_mid_db": db_ratio(side_hw, mid_hw),
        "native_side_to_mid_db": db_ratio(side_native, mid_native),
    }


def main():
    p = argparse.ArgumentParser()
    for field in ("reference", "native", "events", "p97-report", "out"):
        p.add_argument("--" + field, required=True)
    args = p.parse_args()

    with open(args.p97_report, encoding="utf-8") as f:
        p97 = json.load(f)
    if p97["compared_seconds"] != 264:
        raise ValueError("P98 requires P97 264-second global comparison")
    rate = 48000
    ref, rr = sf.read(args.reference, dtype="float32", always_2d=True)
    native, nr = sf.read(args.native, dtype="float32", always_2d=True)
    if (rr, nr) != (48000, 44100):
        raise ValueError("Unexpected sample rates {} {}".format(rr, nr))
    native = resample_poly(native, 160, 147, axis=0)
    lag_s = p97["original_hardware_relative_latency_ms"] / 1000.0
    lag_frames = round(lag_s * rate)
    if lag_frames >= 0:
        ref = ref[lag_frames:]
    else:
        native = native[-lag_frames:]
    ref = ref[:264*rate]
    native = native[:264*rate]
    if len(ref) < 264*rate or len(native) < 264*rate:
        raise ValueError("Incomplete waveform after P97 alignment")
    gain_db = p97["hardware_to_native_global_gain_match_db"]
    native = native * float(10 ** (gain_db / 20.0))
    subtests = find_subtests(load_events(args.events))
    groups = []
    for effect, variant, notes in subtests:
        record = {"effect": effect, "variant": variant, "notes": []}
        for n in notes:
            start = n["on_s"]
            metrics = {}
            for name, wlo, whi in WINDOWS:
                if start + whi > n["off_s"]:
                    raise ValueError("MIDI onset/offset window overlap")
                metrics[name] = measure(ref, native, rate, start + wlo, start + whi)
            # Every note-off is only 125 ms before the next note. Explicitly
            # label the tail window as contaminated by prior effect returns.
            metrics["first_100ms_after_off"] = measure(
                ref, native, rate, n["off_s"], n["off_s"] + 0.1)
            a = int((start + 0.35) * rate)
            b = int((start + 1.35) * rate)
            metrics["body_spectral_bands"] = band_delta(ref[a:b], native[a:b], rate)
            record["notes"].append({**n, "metrics": metrics})
        record["summary"] = {}
        for w in ("onset", "body", "late", "first_100ms_after_off"):
            per_note = [x["metrics"][w]["native_minus_hardware_rms_db"]
                        for x in record["notes"]]
            record["summary"][w] = {
                "mean_rms_difference_db": round(float(np.mean(per_note)), 3),
                "min_db": round(float(min(per_note)), 3),
                "max_db": round(float(max(per_note)), 3),
                "by_send_step_db": per_note,
            }
        groups.append(record)

    report = {
        "experiment": "P98 original SoundFont Spec Test v3.0 effect send subtests",
        "source_p97_global_gain_db": gain_db,
        "source_p97_latency_ms": p97["original_hardware_relative_latency_ms"],
        "source": "CT4390 analog 48kHz FLAC vs native Win95-driver-profile 86Box EMU8000",
        "subtests": groups,
        "limitations": [
            "Original AWE64 Gold hardware was analog RCA, not S/PDIF.",
            "Single global P97 gain used, no per-note, per-group or spectral fitting.",
            "A and C use DIFFERENT MIDI note numbers for different send steps; do not "
            "interpret cross-note ratios as isolated reverb/chorus DSP impulse responses.",
            "Reverb/chorus tails of preceding notes overlap later notes. First 100ms "
            "after each note-off is not an uncontaminated isolated DSP tail.",
            "50ms coarse P97 alignment is retained; this does not establish phase parity.",
            "Separate genuine digital captures are required for exact hardware parity.",
        ],
    }
    Path(args.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("P98 A/B/C original MIDI note groups verified: {}".format(
        ", ".join(g["effect"] + "/" + g["variant"] for g in groups)))
    for group in groups:
        s = group["summary"]["body"]
        print("P98 {} {} body global-gain-matched: mean {:+.3f} dB, "
              "individual {}".format(
                  group["effect"], group["variant"],
                  s["mean_rms_difference_db"], s["by_send_step_db"]))


if __name__ == "__main__":
    main()
