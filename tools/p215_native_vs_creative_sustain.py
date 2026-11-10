#!/usr/bin/env python3
"""P215 genuine frozen P214 Creative Win95 DCYSUS vs actual 125A native 86Box traces.

Does not evaluate a Python re-implementation as proof. The oracle is the
unaltered historical P214 original Creative observed register file. Both
125A native variants must be built separately and play the SHA-pinned P214
SoundFont through the actual 86Box EMU8000 chip integration.

Research-only. Passing does not validate physical hardware, ASIO or VST3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from copy import deepcopy

from p89_compare_voice_registers import native_trace
from p210_compare_creative_eg1 import word
from p214_clone_instrument_matrix import BASES, TARGETS, CASES, SCHEMA as BANK_SCHEMA

DRIVER_SHA = "d343f2428ab3e593c9e42a668cf521b7801e1239792eaf7f2b11b5f179bc7c9a"
SOURCE_BLOB = "4768c4a0215abf49c7a2bb51ada5ba3494faa1c5"
BANK_SHA = "fd49ab51447262e843d3d547290a12aad2176553f47ec66c30039f3844dcc97c"
P214_RUN = 42737751948
P214_ARTIFACT = 13727998644
ORACLE_SCHEMA = "P214-genuine-Win95-Creative-instrument-base-registers-locked-v1"


def require(ok, why):
    if not ok:
        raise ValueError("P215 REJECTED ORIGINAL-DRIVER EVIDENCE: " + why)


def validate_original(oracle, manifest):
    require(oracle.get("schema") == ORACLE_SCHEMA and
            oracle.get("source_run") == P214_RUN and
            oracle.get("source_artifact_id") == P214_ARTIFACT and
            oracle.get("source_original_Creative_vxd_sha256") == DRIVER_SHA and
            oracle.get("source_public_sf2_git_blob") == SOURCE_BLOB and
            oracle.get("source_derived_sf2_sha256") == BANK_SHA and
            oracle.get("physical_Creative_board_present") is False and
            oracle.get("original_SF2_samples_embedded") is False,
            "not the recorded original 1998 Creative Windows95 run P214")
    require(manifest.get("schema") == BANK_SCHEMA and
            manifest.get("public_original_source_git_blob") == SOURCE_BLOB and
            manifest.get("sf2_sha256") == BANK_SHA and
            manifest.get("original_audio_pcm_byte_identical") is True and
            manifest.get("original_25_instruments_preserved") is True and
            manifest.get("original_six_presets_preserved") is True and
            manifest.get("original_44_sample_records_preserved") is True,
            "candidate native SF2 not the original-driver tested source-derived bank")
    cases = oracle.get("cases", [])
    programs = manifest.get("cases", [])
    require(len(cases) == len(programs) == len(CASES) == 28,
            "not all 28 historically captured Win95 Creative cases")
    rows = []
    for (program, base, target), ref, generated in zip(CASES, cases, programs):
        delta = target - base
        require(ref.get("program") == program and
                ref.get("instrument_sustain_base") == base and
                ref.get("requested_sustain") == target and
                ref.get("preset_sustain_delta") == delta,
                "original Creative reference case values/order changed")
        require(generated.get("program") == program and
                generated.get("base_instrument_sustain") == base and
                generated.get("sustain_mod_env_permille") == target and
                generated.get("preset_sustain_delta") == delta and
                generated.get("note") == 59 and generated.get("sample_id") == 43,
                "derived SF2 instrument / preset provenance mismatched original")
        try:
            start = int(ref["creative_dcysus_first_write"], 16)
            release = int(ref["creative_dcysus_release_write"], 16)
        except (KeyError,TypeError,ValueError) as exc:
            raise ValueError("malformed original driver hexadecimal register bytes") from exc
        require(start >> 8 <= 127 and (start & 0xff) == 0x27 and
                release == 0x8027,
                "unexpected original Creative mod-envelope decay/release code")
        rows.append((program, base, target, delta, start, release))
    require(len({(x[1],x[2]) for x in rows}) == 28 and
            {x[1] for x in rows} == set(BASES) and
            {x[2] for x in rows} == set(TARGETS),
            "original driver input matrix lost coverage")
    return rows


def selftest(oracle, manifest):
    rows = validate_original(oracle, manifest)
    mutations = [
        lambda x,y:x["cases"][4].update({"creative_dcysus_first_write":"0xFFFF"}),
        lambda x,y:x["cases"][8].update({"instrument_sustain_base":500}),
        lambda x,y:x["cases"][18].update({"requested_sustain":999}),
        lambda x,y:x.update({"source_run":0}),
        lambda x,y:x.update({"source_original_Creative_vxd_sha256":"0"*64}),
        lambda x,y:y.update({"sf2_sha256":"1"*64}),
        lambda x,y:y["cases"][14].update({"preset_sustain_delta":11}),
        lambda x,y:y.update({"original_audio_pcm_byte_identical":False}),
        lambda x,y:x["cases"].pop(),
    ]
    for mutate in mutations:
        a,b = deepcopy((oracle,manifest))
        mutate(a,b)
        try:
            validate_original(a,b)
        except ValueError:
            continue
        raise AssertionError("deliberately corrupted P214 original evidence was accepted")
    print("P215 original 28-case provenance selftest PASS; 9 independent malformed evidence mutations rejected")
    return rows


def inspect_trace(native, expected_program):
    # The full actual 125A emulated hardware note-on/off, not a mathematical
    # reproduction of a parser's return value.
    require(native and len({v for v,_,_ in native}) == 1,
            "native trace must contain exactly one active voice")
    dcysus = word(native, "DCYSUS")
    require(len(dcysus) == 2,
            f"native program {expected_program}: exactly 2 DCYSUS writes required")
    require(0 <= dcysus[0] >> 8 <= 127 and dcysus[1] & 0x8000,
            "malformed native EG1 register writes")
    return dcysus


def run(oracle, manifest, bank, baseline_dir, candidate_dir):
    rows = selftest(oracle,manifest)
    require(bank.is_file() and hashlib.sha256(bank.read_bytes()).hexdigest() == BANK_SHA,
            "native tested bank bytes are not P214 original Win95 input")
    results = []
    for program, base, target, delta, expected_start, expected_release in rows:
        name = f"B0_P{program}_N59_native-port-write.trace"
        b = native_trace(baseline_dir / name)
        c = native_trace(candidate_dir / name)
        breg,creg = inspect_trace(b,program),inspect_trace(c,program)
        require(len(b)==len(c),"baseline/candidate register sequence count differs")
        # No other voice register, note-on note-off event, or parameter
        # is permitted to change in this narrowly scoped EG1 experiment.
        unchanged = [(v,k,x) for v,k,x in b if k!="DCYSUS"]
        candidate_other = [(v,k,x) for v,k,x in c if k!="DCYSUS"]
        require(unchanged == candidate_other,
                "native candidate changed unrelated voice register sequence")
        require(breg[1] == creg[1],
                "candidate changed modulation envelope RELEASE register unexpectedly")
        require((breg[0]&255)==(creg[0]&255),
                "candidate changed original decay-rate low byte unexpectedly")
        results.append({
            "program":program,"instrument_sustain_base":base,
            "preset_sustain_delta":delta,"requested_sustain":target,
            "original_creative_dcysus":f"0x{expected_start:04X}",
            "original_creative_release":f"0x{expected_release:04X}",
            "native_baseline_dcysus":[f"0x{v:04X}" for v in breg],
            "native_candidate_dcysus":[f"0x{v:04X}" for v in creg],
            "baseline_sustain_high_matches_original":(breg[0]>>8)==(expected_start>>8),
            "candidate_sustain_high_matches_original":(creg[0]>>8)==(expected_start>>8),
            "candidate_exact_original_dcysus":creg[0] == expected_start,
            "original_release_matches_candidate":creg[1] == expected_release,
            "all_other_native_voice_registers_bit_identical":True,
        })
    baseline=sum(x["baseline_sustain_high_matches_original"] for x in results)
    candidate=sum(x["candidate_sustain_high_matches_original"] for x in results)
    new_matches=sum(x["candidate_sustain_high_matches_original"] for x in results
                    if x["instrument_sustain_base"]!=500)
    control_matches=sum(x["candidate_sustain_high_matches_original"] for x in results
                        if x["instrument_sustain_base"]==500)
    improved = baseline < candidate and any(
        a["native_baseline_dcysus"]!=a["native_candidate_dcysus"] for a in results)
    parity = candidate==28 and new_matches==21 and control_matches==7
    return {
        "candidate_creative_high_byte_parity_pass":parity,
        "baseline_to_candidate_improvement_detected":improved,
        "schema":"P215-native-86Box-layered-SF2-EG1-Sustain-vs-genuine-Creative-P214-v1",
        "original_creative_run":P214_RUN,
        "original_creative_artifact":P214_ARTIFACT,
        "original_creative_vxd_sha256":DRIVER_SHA,
        "source_derived_original_bank_sha256":BANK_SHA,
        "actually_executed_86box_native_soundfont":True,
        "candidate_research_build_only":True,
        "candidate_matches_original_28":candidate,
        "baseline_matches_original_28":baseline,
        "candidate_new_instrument_bases_matches_21":new_matches,
        "candidate_original_instrument_base_controls_matches_7":control_matches,
        "genuine_original_Creative_reexecuted_in_this_workflow":False,
        "physical_hardware_parity_proven":False,
        "DAW_ASIO_or_shipping_VST3_tested":False,
        "release":"NO-GO",
        "cases":results,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--oracle",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--sf2",type=Path,required=True)
    p.add_argument("--native-baseline-dir",type=Path,required=True)
    p.add_argument("--native-candidate-dir",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=run(json.loads(a.oracle.read_text()),json.loads(a.manifest.read_text()),
               a.sf2,a.native_baseline_dir,a.native_candidate_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print("P215 native real 86Box SF2 voice: candidate",result["candidate_matches_original_28"],
          "/28 original Creative Win95 Sustain; old baseline",result["baseline_matches_original_28"],
          "/28; all non-DCYSUS voice writes unchanged")
    print("Research only, original driver not reexecuted, physical hardware and DAW NOT RUN")
    if not result["candidate_creative_high_byte_parity_pass"] or not result["baseline_to_candidate_improvement_detected"]:
        raise SystemExit("P215 RESEARCH FAIL: candidate does not reproduce all genuine original Creative Sustain high bytes, or did not improve baseline; forensic JSON retained")


if __name__=="__main__":
    main()
