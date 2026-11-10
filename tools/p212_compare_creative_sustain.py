#!/usr/bin/env python3
"""P212: compare NEW actual original Win95 Creative EG1 sustain registers.

Only authentic new 86Box/Win95/Creative MIDI captures count as measurements.
P211 predictions are evaluated *after* data extraction. Hypothesis mismatch is
an empirical finding, not a reason to falsify the original trace or its labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from p89_compare_voice_registers import original_csv
from p210_compare_creative_eg1 import word
from p212_clone_sf2 import (
    ARCHIVED_P210, NEW_PROGRAMS, REPEATED_CONTROLS, SCHEMA, SUSTAIN_VALUES,
    SOURCE_GIT_BLOB, validate_plan,
)

ORIGINAL_P210_CONTROLS = {0: 127, 250: 95, 750: 33, 1000: 1}


def require(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError("P212 ORIGINAL-DRIVER EVIDENCE INVALID: " + why)


def predictions(n: int) -> dict[str, int]:
    """Integer-only independent calculation; ties-to-even without floating point."""
    require(type(n) is int and 0 <= n <= 1000, "SF2 EG1 sustain out of range")
    whole, remainder = divmod(126 * n, 1000)
    if 2 * remainder > 1000 or (2 * remainder == 1000 and whole % 2 == 1):
        whole += 1
    # P211 proposal; separately retain the old alternatives for diagnostic contrast.
    return {
        "p211_126_ties_even": 127 - whole,
        "old_127_truncate": 127 - (127 * n // 1000),
        "old_127_round_half_up": 127 - ((2 * 127 * n + 1000) // 2000),
        "126_round_half_up": 127 - ((2 * 126 * n + 1000) // 2000),
    }


def validate_sources(manifest: dict, guest: dict, verification: dict) -> list[dict]:
    validate_plan(SUSTAIN_VALUES)
    require(manifest.get("schema") == SCHEMA, "wrong generator manifest")
    require(manifest.get("public_original_source_git_blob") == SOURCE_GIT_BLOB,
            "original SoundFont source drift")
    require(manifest.get("preserved_original_audio_samples") is True and
            manifest.get("preserved_original_6_presets") is True and
            manifest.get("independent_unseen_sustain_values") == 24 and
            manifest.get("repeated_original_driver_controls") == sorted(REPEATED_CONTROLS),
            "non-original SoundFont or misrepresented independence")
    p = manifest.get("programs", [])
    require(len(p) == 28 and
            [x.get("program") for x in p] == list(NEW_PROGRAMS) and
            [x.get("sustain_mod_env_permille") for x in p] == list(SUSTAIN_VALUES) and
            all(x.get("hold_mod_env_tc") == 0 and x.get("note") == 59 and
                x.get("sample_id") == 43 for x in p),
            "changed preset generator plan")
    require(verification.get("agent_launched_in_actual_win95") is True and
            verification.get("original_creative_winmm_endpoint_selected") is True and
            verification.get("original_creative_com1_ready") is True and
            not verification.get("win95_agent_error") and
            verification.get("creatives_midi_short_messages_delivered", 0) >= 112 and
            verification.get("audio_observed") is True and
            verification.get("p84_universal_sf2_test") is True,
            "original Win95 Creative WinMM/COM1/device/audio not verified")
    require(guest.get("hardware") == "sbawe64_gold" and
            guest.get("sample_ram_kib") == 28672 and
            guest.get("p84_universal_sf2_test") is True and
            guest.get("p75_private_sample_upload_plausible") is True and
            guest.get("p75_private_sample_upload_write_words", 0) >=
            guest.get("p75_private_sample_upload_minimum_words", 1),
            "correct emulated device or uploaded original sample bank not verified")
    trial = guest.get("p64_original_win95_midi", {})
    require(trial.get("p212_real_win95_driver_sweep") is True and
            not trial.get("p210_real_win95_driver_sweep"),
            "P211 archived source or old P210 sweep replayed instead of new driver run")
    windows = trial.get("p212_original_creative_register_windows", [])
    require(len(windows) == 28 and
            [x.get("program") for x in windows] == list(NEW_PROGRAMS),
            "missing, duplicated or reordered new Creative program windows")
    previous_end = -1
    for window in windows:
        start, end = window.get("start_row"), window.get("end_row")
        require(type(start) is int and type(end) is int and
                start >= previous_end and end > start and
                window.get("window_isolated") is True and
                window.get("note") == 59 and window.get("velocity") == 100,
                "invalid, overlapping or unspecific original Creative note window")
        previous_end = end
    return windows


def selftest() -> None:
    assert predictions(0)["p211_126_ties_even"] == 127
    assert predictions(4)["p211_126_ties_even"] == 126
    assert predictions(250)["p211_126_ties_even"] == 95
    assert predictions(500)["p211_126_ties_even"] == 64
    assert predictions(750)["p211_126_ties_even"] == 33
    assert predictions(1000)["p211_126_ties_even"] == 1
    assert predictions(750)["126_round_half_up"] == 32
    p = [{"program": program, "note": 59, "hold_mod_env_tc": 0,
          "sample_id": 43, "sustain_mod_env_permille": value}
         for program, value in zip(NEW_PROGRAMS, SUSTAIN_VALUES)]
    m = {"schema": SCHEMA, "public_original_source_git_blob": SOURCE_GIT_BLOB,
         "preserved_original_audio_samples": True, "preserved_original_6_presets": True,
         "independent_unseen_sustain_values": 24,
         "repeated_original_driver_controls": sorted(REPEATED_CONTROLS),
         "programs": p}
    g = {"hardware": "sbawe64_gold", "sample_ram_kib": 28672,
         "p84_universal_sf2_test": True,
         "p75_private_sample_upload_plausible": True,
         "p75_private_sample_upload_write_words": 100,
         "p75_private_sample_upload_minimum_words": 50,
         "p64_original_win95_midi": {
             "p212_real_win95_driver_sweep": True,
             "p212_original_creative_register_windows": [
                 {"program": pr, "start_row": i * 100, "end_row": i * 100 + 50,
                  "window_isolated": True, "note": 59, "velocity": 100}
                 for i, pr in enumerate(NEW_PROGRAMS)]}}
    v = {"agent_launched_in_actual_win95": True,
         "original_creative_winmm_endpoint_selected": True,
         "original_creative_com1_ready": True,
         "win95_agent_error": False, "creatives_midi_short_messages_delivered": 112,
         "audio_observed": True, "p84_universal_sf2_test": True}
    assert len(validate_sources(m, g, v)) == 28
    mutants = [
        lambda a,b,c: a.update({"public_original_source_git_blob": "wrong"}),
        lambda a,b,c: a["programs"].pop(),
        lambda a,b,c: a["programs"][1].update({"sustain_mod_env_permille": 3}),
        lambda a,b,c: b["p64_original_win95_midi"]["p212_original_creative_register_windows"][3].update({"program": 102}),
        lambda a,b,c: b["p64_original_win95_midi"]["p212_original_creative_register_windows"][2].update({"start_row": 0}),
        lambda a,b,c: b["p64_original_win95_midi"].update({"p212_real_win95_driver_sweep": False}),
        lambda a,b,c: c.update({"original_creative_winmm_endpoint_selected": False}),
        lambda a,b,c: c.update({"audio_observed": False}),
        lambda a,b,c: b.update({"p75_private_sample_upload_plausible": False}),
        lambda a,b,c: c.update({"creatives_midi_short_messages_delivered": 111}),
    ]
    for mutant in mutants:
        a, b, c = deepcopy((m, g, v))
        mutant(a, b, c)
        try:
            validate_sources(a, b, c)
        except ValueError:
            continue
        raise AssertionError("P212 falsely accepted deliberately corrupted evidence")
    print("P212 comparator selftest PASS: boundary arithmetic and 10 rejected provenance/window mutations")


def audit(args) -> dict:
    m = json.loads(args.manifest.read_text(encoding="utf-8"))
    g = json.loads(args.guest_report.read_text(encoding="utf-8"))
    v = json.loads(args.guest_verification.read_text(encoding="utf-8"))
    windows = validate_sources(m, g, v)
    require(args.derived_sf2.is_file() and
            hashlib.sha256(args.derived_sf2.read_bytes()).hexdigest() == m.get("sf2_sha256"),
            "actual Win95 input SoundFont does not match committed manifest")
    cases = []
    for setting, window in zip(m["programs"], windows):
        regs = original_csv(args.creative_csv, window["start_row"], window["end_row"])
        require(len({voice for voice, _key, _value in regs}) == 1,
                "overlapping or voice-stolen original driver oracle")
        hold_writes = word(regs, "ATKHLD")
        sustain_writes = word(regs, "DCYSUS")
        require(len(hold_writes) == 1 and len(sustain_writes) == 2,
                "incomplete original Win95 envelope register writes")
        observed = sustain_writes[0] >> 8
        require(0 <= observed <= 127, "driver sustain high byte outside 0..127")
        value = setting["sustain_mod_env_permille"]
        if value in REPEATED_CONTROLS:
            require(observed == ORIGINAL_P210_CONTROLS[value],
                    "original P210 repeat control failed: different register interpretation or driver path")
        models = predictions(value)
        cases.append({
            "program": setting["program"],
            "sustain_permille": value,
            "previously_unseen_in_P210": value not in ARCHIVED_P210,
            "original_creative_dcysus_writes": [f"0x{w:04X}" for w in sustain_writes],
            "original_creative_sustain_high_byte": observed,
            "predicted": models,
            "hypothesis_matches": observed == models["p211_126_ties_even"],
        })
    require(len(cases) == 28 and
            sum(x["previously_unseen_in_P210"] for x in cases) == 24,
            "invalid independence count in evidence")
    model_keys = tuple(predictions(0))
    stats = {model: {
        "matched_all_28": sum(x["original_creative_sustain_high_byte"] == x["predicted"][model] for x in cases),
        "matched_24_new": sum(x["previously_unseen_in_P210"] and
                              x["original_creative_sustain_high_byte"] == x["predicted"][model] for x in cases),
    } for model in model_keys}
    result = {
        "schema": "P212-genuine-Creative-Win95-independent-sustain-register-v1",
        "original_creative_driver_reexecuted": True,
        "driver": "Creative SBAWE.VXD/WinMM in actual emulated Windows 95 guest",
        "emu8000": "86Box emulated AWE64 Gold, not physical silicon",
        "original_public_sf2_git_blob": SOURCE_GIT_BLOB,
        "derived_sf2_sha256": m["sf2_sha256"],
        "note": 59, "velocity": 100, "new_values": 24, "independent_repeat_controls": 4,
        "original_eg1_sustain_register_cases": cases,
        "candidate_model_stats": stats,
        "p211_hypothesis_matches_all_28": stats["p211_126_ties_even"]["matched_all_28"] == 28,
        "p211_hypothesis_matches_new_24": stats["p211_126_ties_even"]["matched_24_new"] == 24,
        "mathematical_formula_globally_proven": False,
        "product_VST3_DSP_modified": False,
        "hardware_and_DAW_validation": "NOT RUN",
        "release_approval": "NO-GO",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("P212 genuine Creative Win95 registered sustain cases", len(cases),
          "(24 new plus 4 independent control repeats)")
    for model, scores in stats.items():
        print(model, scores)
    if not result["p211_hypothesis_matches_all_28"]:
        print("P212 RESEARCH RESULT: P211 candidate DISPROVED for at least one measured setting; CI is evidence-only")
    else:
        print("P212 RESEARCH RESULT: P211 candidate matches 28/28 genuine new-run cases; formula still not globally proven")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    for name in ("manifest", "guest_report", "guest_verification", "creative_csv",
                 "derived_sf2", "out"):
        ap.add_argument("--" + name.replace("_", "-"), dest=name, type=Path)
    args = ap.parse_args()
    selftest()
    if args.self_test and not args.manifest:
        return
    require(all(getattr(args, x) for x in
                ("manifest", "guest_report", "guest_verification", "creative_csv", "derived_sf2", "out")),
            "original driver artifacts required")
    audit(args)


if __name__ == "__main__":
    main()
