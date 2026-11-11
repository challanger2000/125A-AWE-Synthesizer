#!/usr/bin/env python3
"""P232 controlled 2x2 original-ROM/SBK *diagnostic*, not original-Creative parity.

A = Chamberlin + EQ; B = Chamberlin / no EQ;
C = upstream 86Box Moog + EQ; D = upstream 86Box Moog / no EQ.
No gain matching, no audio normalization, no preset changes.
All four variants must have identical note and chip-register traces.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import wave
from pathlib import Path

import numpy as np

from p230_rom_sbk_ab import bands, envelope
from p89_compare_voice_registers import native_trace

VARIANTS = {
    "A": ("measured-fx", "Chamberlin", True),
    "B": ("no-eq", "Chamberlin", False),
    "C": ("moog-eq", "original_86box_Moog", True),
    "D": ("moog-no-eq", "original_86box_Moog", False),
}
PROGRAMS = (0, 39, 80, 88, 112)
ROM_SHA = "4e143b94f758734f594ded78f4e5115635975c16fa37fabeae0baa4938ca710e"
SBK_SHA = "fd2e35a260fef22fe809918dda3c921c6d48d53a29c3515af8a41019ce72d586"
RATE = 44100
FRAMES = RATE * 2


def demand(condition: bool, description: str) -> None:
    if not condition:
        raise ValueError("P232_2X2_ABORT: " + description)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def case_file(program: int) -> str:
    return f"gm_b16383_p{program:03d}_n060_v100.wav"


def read_wave(path: Path) -> tuple[np.ndarray, int, str]:
    demand(path.is_file(), f"missing PCM {path}")
    with wave.open(str(path), "rb") as wav:
        demand((wav.getframerate(), wav.getnchannels(), wav.getsampwidth(),
                wav.getnframes(), wav.getcomptype()) ==
               (RATE, 2, 2, FRAMES, "NONE"), f"invalid format/length {path}")
        pcm = wav.readframes(FRAMES)
    demand(len(pcm) == FRAMES * 4, f"truncated audio {path}")
    raw = np.frombuffer(pcm, dtype="<i2").reshape(-1, 2)
    demand(np.any(raw), f"silent audio {path}")
    return raw.astype(np.float64) / 32768.0, int(np.count_nonzero(
        (raw == -32768) | (raw == 32767))), hashlib.sha256(pcm).hexdigest()


def db(value: float) -> float:
    return round(20.0 * math.log10(max(value, 1e-16)), 4)


def rms_db(samples: np.ndarray) -> float:
    return db(float(np.sqrt(np.mean(samples ** 2))))


def spectrum_db(samples: np.ndarray) -> dict[str, float]:
    return {band: round(10.0 * math.log10(max(power, 1e-25)), 4)
            for band, power in bands(samples).items()}


def envelope_similarity(a: np.ndarray, b: np.ndarray) -> float:
    first, second = envelope(a), envelope(b)
    denom = np.linalg.norm(first - first.mean()) * np.linalg.norm(second - second.mean())
    if denom < 1e-15:
        return 1.0 if np.array_equal(first, second) else 0.0
    return round(float(np.dot(first - first.mean(), second - second.mean()) / denom), 6)


def metric(pcm: np.ndarray, rails: int, digest: str) -> dict:
    return {
        "pcm_sha256": digest,
        "rms_dbfs": rms_db(pcm),
        "peak_dbfs": db(float(np.max(np.abs(pcm)))),
        "rail_samples": rails,
        "clipped": rails > 0,
        "bands_power_db": spectrum_db(pcm),
    }


def validate_matrix(root: Path, previous: dict) -> tuple[dict, dict]:
    demand(previous.get("real_original_driver_guest") is True,
           "prior numeric reference has no original Creative Win95 proof")
    demand(previous.get("wave_rom_sha256") == ROM_SHA and
           previous.get("original_sbks_verified_sha256") == SBK_SHA,
           "original Creative asset hashes do not match current ROM/SBK")
    old = {int(case["program"]): case for case in previous.get("cases", [])}
    demand(set(old) == set(PROGRAMS), "expected exactly five prior original GM reference metrics")
    demand(len(previous.get("unresolved_original_audio_cases", [])) == 3,
           "three previously invalid original drum references must remain excluded")

    for key, (directory, _, _) in VARIANTS.items():
        folder = root / directory
        manifest = folder / "cases.csv"
        demand(manifest.is_file(), f"missing manifest for {key}")
        with manifest.open(newline="", encoding="utf8") as handle:
            rows = list(csv.DictReader(handle))
        # The P230 pilot has eight native notes, but the three drum originals are
        # unfit for a valid A/B. Keep them separate from the 5-case factorial.
        demand(len(rows) == 8 and len({r["file"] for r in rows}) == 8,
               f"invalid MIDI matrix for {key}")
        demand({case_file(p) for p in PROGRAMS} <= {r["file"] for r in rows},
               f"missing GM programs in {key}")
        for row in rows:
            demand(row["velocity"] == "100" and
                   row["channel"] in ("0", "9"), f"invalid MIDI settings in {key}")
    return old, {"tested_gm_programs": list(PROGRAMS),
                 "excluded_original_drum_reference_count": 3}


def compare(root: Path, previous: dict) -> dict:
    old, common = validate_matrix(root, previous)
    cases = []
    trace_totals = {"consistent": 0, "cases": len(PROGRAMS)}
    for program in PROGRAMS:
        filename = case_file(program)
        audio: dict[str, np.ndarray] = {}
        results: dict[str, dict] = {}
        reference_registers = None
        trace_hashes = {}
        for key, (directory, filter_mode, eq_on) in VARIANTS.items():
            wav = root / directory / filename
            pcm, rails, digest = read_wave(wav)
            m = metric(pcm, rails, digest)
            m["filter"] = filter_mode
            m["eq"] = "on" if eq_on else "off"
            audio[key], results[key] = pcm, m
            trace = root / directory / "traces" / (filename + ".trace")
            registers = native_trace(trace)
            demand(len(registers) >= 12, f"insufficient register events in {key} {filename}")
            if reference_registers is None:
                reference_registers = registers
            else:
                demand(reference_registers == registers,
                       f"actual EMU8000 register sequence mismatch {filename}, A vs {key}")
            trace_hashes[key] = hashlib.sha256(
                json.dumps(registers, separators=(",", ":")).encode()).hexdigest()
        demand(len(set(trace_hashes.values())) == 1,
               f"register trace digest mismatch for program {program}")
        trace_totals["consistent"] += 1

        for key in VARIANTS:
            results[key]["envelope_corr_with_A"] = envelope_similarity(audio["A"], audio[key])
            results[key]["waveform_corr_with_A"] = round(float(
                np.dot(audio["A"].ravel(), audio[key].ravel()) /
                (np.linalg.norm(audio["A"]) * np.linalg.norm(audio[key]))), 6)
        def delta(a: str, b: str) -> float:
            return round(results[a]["rms_dbfs"] - results[b]["rms_dbfs"], 4)
        effects = {
            "filter_Moog_minus_Chamberlin_eq_on_db": delta("C", "A"),
            "filter_Moog_minus_Chamberlin_eq_off_db": delta("D", "B"),
            "eq_on_minus_off_Chamberlin_db": delta("A", "B"),
            "eq_on_minus_off_Moog_db": delta("C", "D"),
            "filter_mean_effect_db": round((delta("C", "A") + delta("D", "B")) / 2, 4),
            "eq_mean_effect_db": round((delta("A", "B") + delta("C", "D")) / 2, 4),
            "filter_eq_interaction_db": round(delta("C", "A") - delta("D", "B"), 4),
        }
        for k in ("B", "C", "D"):
            results[k]["band_power_delta_vs_A_db"] = {
                band: round(level - results["A"]["bands_power_db"][band], 4)
                for band, level in results[k]["bands_power_db"].items()}
        old_reference_rms = float(old[program]["metrics"]["reference_rms_dbfs"])
        historical = {
            "original_creative_rms_dbfs": old_reference_rms,
            "NOT_VALID_EQUAL_STATE_AB": True,
            "reason": "Prior original Win95 audio not re-captured or proven equal FX timing/render/capture conditions",
            "original_minus_variant_rms_db": {
                key: round(old_reference_rms - results[key]["rms_dbfs"], 4)
                for key in VARIANTS},
        }
        cases.append({
            "program": program, "midi_note": 60, "velocity": 100,
            "register_series_identical_all_four": True,
            "normalized_register_trace_sha256": trace_hashes["A"],
            "variants": results, "factorial_effects": effects,
            "historical_original_numeric_diagnostic_only": historical,
            "sample_exact_A_vs_B": bool(np.array_equal(audio["A"], audio["B"])),
            "sample_exact_A_vs_C": bool(np.array_equal(audio["A"], audio["C"])),
            "sample_exact_A_vs_D": bool(np.array_equal(audio["A"], audio["D"])),
        })
    result = {
        "schema": "125A-P232-2x2-v1",
        "kind": "CONTROLLED_DIAGNOSIS_NOT_EQUAL_STATE_ORIGINAL_AB",
        "source_of_original_numeric": "private P231 original Win95 Creative register/PCM run 42929093165",
        "genuine_wave_rom_sha256": ROM_SHA, "genuine_synthgm_sbk_sha256": SBK_SHA,
        "test_conditions": {
            "sample_rate_hz": RATE, "frames": FRAMES, "channels": 2, "pcm": "signed16",
            "MIDI": "C4 note 60, velocity 100, channel 1, 1s gate, 1s release",
            "chip_register_traces": "exactly identical within each five-program A/B/C/D group",
            "effective_reverb_send": "0x1C, patched to measured original post-note in all four variants",
            "effective_chorus_send": "program 88 voice sends 0x77 and 0x7B, zero for other four",
            "native_gui_effect_overrides": "both 0%, then diagnostic original sends restored",
            "fx_return": "enabled in all four, same compiled FX core",
            "output": "2 seconds, 44.1kHz, stereo PCM16, 86Box-derived P230 renderer; no normalization",
            "difference_from_original_win95": "original Win95 note/timing/return/capture parity NOT VERIFIED",
            "variants": {k: {"filter": v[1], "eq_on": v[2]} for k, v in VARIANTS.items()},
        },
        "cases": cases, "trace_proof": trace_totals,
        "diagnostic_native_waveforms": len(PROGRAMS) * len(VARIANTS),
        "historical_creative_reference_equal_state_compared": 0,
        "valid_original_AB_pairs": 0, "original_AB_tolerance_passed": 0,
        "fixed_original_AB_failures": 0, "original_AB_regressions": 0,
        "unresolved_original_drum_references": 3,
        "validity": "NO-GO until original PCM is re-captured under proven identical registers, FX, chip and capture settings",
        "release": "BLOCKED",
        **common,
    }
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--original-numeric", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--source-sha", required=True)
    args = ap.parse_args()
    demand(not args.out.exists(), "refuse overwriting previous 2x2 evidence")
    prior_bytes = args.original_numeric.read_bytes()
    previous = json.loads(prior_bytes)
    result = compare(args.root, previous)
    result["original_numeric_reference_sha256"] = hashlib.sha256(prior_bytes).hexdigest()
    result["source_125a_commit"] = args.source_sha
    result["runner_A_emu8k_source_sha256"] = sha_file(args.root / "original-snd_emu8k.c")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf8")
    print("P232_2x2_FILTER_EQ_DIAGNOSTIC: five original ROM/SBK GM programs, all four variants")
    print("MIDI/REGISTER/FX/OUTPUT same within A/B/C/D; DO NOT CLAIM ORIGINAL-DRIVER AUDIO PASS")
    print("program | A RMS dBFS | B RMS dBFS | C RMS dBFS | D RMS dBFS | filter effect EQ on / off | EQ effect chamberlin / moog | clipping A/B/C/D")
    for row in result["cases"]:
        x = row["variants"]
        effect = row["factorial_effects"]
        print(f'{row["program"]:>3} | {x["A"]["rms_dbfs"]:>8.3f} | '
              f'{x["B"]["rms_dbfs"]:>8.3f} | {x["C"]["rms_dbfs"]:>8.3f} | '
              f'{x["D"]["rms_dbfs"]:>8.3f} | '
              f'{effect["filter_Moog_minus_Chamberlin_eq_on_db"]:+.3f}/'
              f'{effect["filter_Moog_minus_Chamberlin_eq_off_db"]:+.3f} | '
              f'{effect["eq_on_minus_off_Chamberlin_db"]:+.3f}/'
              f'{effect["eq_on_minus_off_Moog_db"]:+.3f} | '
              f'{"/".join(str(x[k]["rail_samples"]) for k in VARIANTS)}')
    print(f'P232_DIAGNOSTIC_MATRIX_PASS 20 native cases, {result["trace_proof"]["consistent"]}/5 identical register traces')
    print("P232_EQUAL_STATE_CREATIVE_AUDIO_COMPARISONS=0 P232_RELEASE=BLOCKED")


if __name__ == "__main__":
    main()
