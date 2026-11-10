#!/usr/bin/env python3
"""P212: precommitted, independent 28-value original Creative sustain experiment.

Append preset-only variants to the already Creative-accepted public SoundFont,
not an unaccepted synthetic-bank substitute. No original media is exported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from p210_clone_verified_sf2 import SOURCE_GIT_BLOB, derive

# Frozen BEFORE the new Creative Windows 95 run. MIDI programs 100..127.
# Four repeats of archived original P210 values are independent run controls.
# The other 24 have never been measured in P210.
SUSTAIN_VALUES = (
    0, 1, 3, 4, 7, 8, 11, 12, 19, 20, 31, 32, 63, 124,
    125, 249, 250, 251, 375, 376, 624, 625, 749, 750,
    751, 875, 993, 1000,
)
ARCHIVED_P210 = frozenset((0, 250, 499, 500, 501, 750, 1000))
REPEATED_CONTROLS = frozenset((0, 250, 750, 1000))
NEW_PROGRAMS = tuple(range(100, 128))
VARIANTS = tuple((0, value) for value in SUSTAIN_VALUES)
SCHEMA = "P212-original-Creative-28-sustain-generators-v1"


def check(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError("P212 SOURCE FIXTURE FAIL: " + reason)


def validate_plan(values: tuple[int, ...]) -> None:
    check(len(values) == len(NEW_PROGRAMS) == 28, "28 controlled programs required")
    check(all(type(v) is int and 0 <= v <= 1000 for v in values), "invalid sustain")
    check(len(set(values)) == len(values), "duplicate sustain value")
    check(tuple(sorted(values)) == values, "nonmonotonic frozen values")
    check(set(values) & ARCHIVED_P210 == REPEATED_CONTROLS,
          "unexpected previously observed P210 values")
    check(len(set(values) - ARCHIVED_P210) == 24, "not 24 independent new values")
    check(all(v in values for v in (0, 4, 8, 249, 250, 251, 749, 750, 751, 993, 1000)),
          "missing boundary, rounding or archived control witness")


def selftest() -> None:
    validate_plan(SUSTAIN_VALUES)
    for bad in (
        SUSTAIN_VALUES[:-1],
        SUSTAIN_VALUES[:-1] + (993,),
        tuple(reversed(SUSTAIN_VALUES)),
        SUSTAIN_VALUES[:3] + (-1,) + SUSTAIN_VALUES[4:],
        SUSTAIN_VALUES[:3] + (1001,) + SUSTAIN_VALUES[4:],
        SUSTAIN_VALUES[:3] + (500,) + SUSTAIN_VALUES[4:],
    ):
        try:
            validate_plan(bad)
        except ValueError:
            continue
        raise AssertionError("P212 invalid sweep plan was accepted")
    print("P212 independent fixture selftest PASS: 28 values, 24 new, 4 repeat controls, 6 rejected mutations")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--source", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--manifest", type=Path)
    args = ap.parse_args()
    selftest()
    if args.self_test and not args.source:
        return
    check(bool(args.source and args.out and args.manifest), "source, out and manifest required")
    original = args.source.read_bytes()
    source_blob = hashlib.sha1(
        b"blob " + str(len(original)).encode("ascii") + b"\0" + original
    ).hexdigest()
    check(source_blob == SOURCE_GIT_BLOB, "original public SoundFont source identity changed")
    derived, programs, instrument = derive(
        original, variants=VARIANTS, new_programs=NEW_PROGRAMS, label_prefix="P212"
    )
    check([p["program"] for p in programs] == list(NEW_PROGRAMS),
          "derived SF2 program mapping differs from frozen plan")
    check([p["sustain_mod_env_permille"] for p in programs] == list(SUSTAIN_VALUES),
          "generated presets differ from frozen sustain values")
    check(all(p["hold_mod_env_tc"] == 0 for p in programs),
          "hold generator introduced an independent variable")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(derived)
    report = {
        "schema": SCHEMA,
        "source": "Creative-accepted public original SoundFont Spec Test v3.0; 28 appended preset-only variants",
        "public_original_source_git_blob": SOURCE_GIT_BLOB,
        "original_sf2_sha256": hashlib.sha256(original).hexdigest(),
        "sf2_sha256": hashlib.sha256(derived).hexdigest(),
        "preserved_original_audio_samples": True,
        "preserved_original_6_presets": True,
        "physical_hardware": False,
        "independent_unseen_sustain_values": 24,
        "repeated_original_driver_controls": sorted(REPEATED_CONTROLS),
        "programs": programs,
        "original_instrument_metadata": instrument,
        "original_sample_pcm_included_in_public_artifact": False,
    }
    args.manifest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("P212 generated: 28 controlled SF2 programs, 24 newly sampled values; derived SHA256", report["sf2_sha256"])


if __name__ == "__main__":
    main()
