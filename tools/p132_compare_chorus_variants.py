"""P132: differential audit of the REAL 86Box chorus kernel in two builds.

Does not compare the original proprietary Creative effect DSP. 32-bit RAW
effect-return units, not exported VST3 audio. 16-bit gain proxy is only a
quantization sensitivity estimate; it omits EQ, reverb and dry mixing.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

RATE = 44100
FRAMES = 4 * RATE
GAIN_NUMERATOR = 57737
PRESETS = (0, 8, 16, 32, 128, 224, 0, 192)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rms(arr):
    f = np.asarray(arr, dtype=np.float64)
    return float(np.sqrt(np.mean(f * f))) if f.size else 0.0


def read_tail(path):
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 8 or [int(x["preset"]) for x in rows] != list(range(8)):
        raise ValueError("Missing or out-of-order feedback-mode cases")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.directory)
    original_tail = read_tail(root / "original-tail.csv")
    candidate_tail = read_tail(root / "candidate-tail.csv")
    records = []
    affected = 0
    for preset, feedback in enumerate(PRESETS):
        before_file = root / f"original-preset-{preset}.raw"
        after_file = root / f"candidate-preset-{preset}.raw"
        expected_bytes = FRAMES * 2 * 4
        if before_file.stat().st_size != expected_bytes or after_file.stat().st_size != expected_bytes:
            raise ValueError(f"Truncated 32-bit real-chip chorus data for preset {preset}")
        before = np.memmap(before_file, mode="r", dtype="<i4", shape=(FRAMES, 2))
        after = np.memmap(after_file, mode="r", dtype="<i4", shape=(FRAMES, 2))
        delta = after.astype(np.int64) - before.astype(np.int64)
        differences = np.count_nonzero(delta)
        maxdelta = int(np.max(np.abs(delta)))
        body = slice(0, int(2.0 * RATE))
        tail = slice(int(3.0 * RATE), FRAMES)
        body_rms = rms(before[body])
        body_diff = rms(delta[body])
        rel_db = (20 * np.log10(body_diff / body_rms)
                  if body_rms > 0 and body_diff > 0 else None)
        # Quantization SENSITIVITY only, not final actual 16-bit output:
        # full chip also mixes dry, reverb and EQ and applies clipping.
        a = ((before.astype(np.int64) * GAIN_NUMERATOR) >> 16).clip(-32768, 32767)
        b = ((after.astype(np.int64) * GAIN_NUMERATOR) >> 16).clip(-32768, 32767)
        quantized_differences = int(np.count_nonzero(a != b))
        o, c = original_tail[preset], candidate_tail[preset]
        if (int(o["feedback"]) != feedback or int(c["feedback"]) != feedback
                or int(o["negative_silent"]) != int(feedback == 0)
                or int(c["negative_silent"]) != 1
                or int(o["positive_silent"]) != 1
                or int(c["positive_silent"]) != 1):
            raise ValueError(f"Unexpected signed decay oracle for preset {preset}")
        if feedback == 0:
            if differences or maxdelta or quantized_differences:
                raise ValueError(f"Feedback-free mode {preset} changed!")
        else:
            affected += differences > 0
        records.append({
            "preset": preset,
            "feedback_byte": feedback,
            "reference_hardware_capture_available": feedback == 0,
            "original_negative_1_lsb_ring_stuck": bool(feedback),
            "candidate_negative_1_lsb_ring_silent": True,
            "original_sha256_pcm32": digest(before_file),
            "candidate_sha256_pcm32": digest(after_file),
            "pcm32_samples_compared": FRAMES * 2,
            "differing_pcm32_samples": int(differences),
            "maximum_absolute_pcm32_lsb": maxdelta,
            "excitation_rms_pcm32": round(body_rms, 6),
            "difference_rms_pcm32": round(body_diff, 6),
            "difference_relative_to_signal_rms_db": (
                round(float(rel_db), 4) if rel_db is not None else None),
            "last_second_max_difference_pcm32_lsb": int(np.max(np.abs(delta[tail]))),
            "last_second_original_nonzero_pcm32_samples": int(np.count_nonzero(before[tail])),
            "last_second_candidate_nonzero_pcm32_samples": int(np.count_nonzero(after[tail])),
            "differing_samples_after_gain_and_16bit_proxy": quantized_differences,
        })
        print(f"P132_DIFF preset={preset} feedback={feedback} "
              f"changed_pcm32_samples={differences} max_delta_lsb32={maxdelta} "
              f"proxy_changed_pcm16={quantized_differences} "
              f"hardware_reference_present={int(feedback==0)}")
    if affected < 1:
        raise ValueError("Candidate made no positive-feedback impulse-PCM changes")
    data = {
        "test": "P132 real-86Box source dual-build Chorus candidate comparison",
        "note": "No physical-hardware PCM was compared; feedback-zero CT4390 evidence cannot decide signed feedback rounding.",
        "sample_rate": RATE,
        "duration_sec_per_mode": FRAMES / RATE,
        "source": "same base code, signed-feedback expression changed only in ephemeral candidate build",
        "limitations": [
            "Synthetic internal effect-return PCM32, not final VST3 output",
            "Quantized gain-only PCM16 proxy excludes dry/reverb/EQ and cannot prove audibility",
            "Creative AWE64 analog CT4390 reference uses Chorus 1 (feedback=0), so cannot validate six positive-feedback modes",
            "Physical 24-bit effects DSP internal rounding remains unknown",
            "Separate matched physical-card capture of feedback presets is required",
        ],
        "presets": records,
        "feedback_presets_with_observed_pcm_change": affected,
        "hardware_parity_proven": False,
        "release_approved": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"P132_COMPARISON_PASS modes=8 affected={affected} "
          "hardware_parity_proven=0 release_approved=0")


if __name__ == "__main__":
    main()
