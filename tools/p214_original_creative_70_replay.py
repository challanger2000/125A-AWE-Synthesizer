#!/usr/bin/env python3
"""P214 replay of *archived* genuine original Creative Win95 DCYSUS registers.
This does not run the original driver again; it rejects damaged oracle data.
"""
from __future__ import annotations
import argparse, json
from copy import deepcopy
from pathlib import Path
from p213_original_creative_sustain_replay import selftest as replay_p213
from p214_clone_instrument_matrix import CASES
from p214_compare_creative_instrument_base import source_derived, T

ORIGINAL_VXD_SHA="d343f2428ab3e593c9e42a668cf521b7801e1239792eaf7f2b11b5f179bc7c9a"
ORIGINAL_SOURCE="4768c4a0215abf49c7a2bb51ada5ba3494faa1c5"
DERIVED_SHA="fd49ab51447262e843d3d547290a12aad2176553f47ec66c30039f3844dcc97c"

def req(ok,reason):
    if not ok:raise ValueError("P214 ORIGINAL CREATIVE FROZEN ORACLE REJECT: "+reason)

def verify_p214(doc):
    req(doc.get("schema")=="P214-genuine-Win95-Creative-instrument-base-registers-locked-v1"
        and doc.get("source_run")==42737751948
        and doc.get("source_artifact_id")==13727998644
        and doc.get("source_original_Creative_vxd_sha256")==ORIGINAL_VXD_SHA
        and doc.get("source_public_sf2_git_blob")==ORIGINAL_SOURCE
        and doc.get("source_derived_sf2_sha256")==DERIVED_SHA,
        "historical Creative source provenance or artifact identity changed")
    req(doc.get("physical_Creative_board_present") is False and
        doc.get("original_SF2_samples_embedded") is False,
        "hardware claim or media boundary changed")
    rows=doc.get("cases")
    req(type(rows) is list and len(rows)==28,
        "missing original Creative register records")
    total=0
    direct=0
    new_base=0
    for row,(program,base,requested) in zip(rows,CASES):
        req((row.get("program"),row.get("instrument_sustain_base"),
              row.get("requested_sustain"),row.get("preset_sustain_delta"))==
            (program,base,requested,requested-base),
            "frozen base/preset MIDI program and additive SF2 generators altered")
        raw=row.get("creative_dcysus_first_write")
        release=row.get("creative_dcysus_release_write")
        req(isinstance(raw,str) and len(raw)==6 and raw.startswith("0x")
            and release=="0x8027","missing original DCYSUS note/release pair")
        try:word=int(raw,16)
        except ValueError as exc:raise ValueError("malformed original register value") from exc
        req(word&0xFF==0x27 and 0<=word>>8<=127,
            "recorded actual Creative DCYSUS register shape changed")
        original=word>>8
        two_stage=source_derived(base,requested-base)
        direct_value=T(requested)
        req(original==two_stage,
            f"source-derived Sustain mismatches original Creative program {program}")
        total+=1
        direct+=original==direct_value
        new_base+=base!=500
    req((total,new_base,direct)==(28,21,16),
        "original Creative matrix or 12 discriminating two-vs-one stage cases changed")
    return total,new_base,direct

def main():
    ap=argparse.ArgumentParser()
    for option in ("p210","p212","p214","out"):
        ap.add_argument("--"+option,required=True,type=Path)
    a=ap.parse_args()
    p210,p212,p214=(json.loads(f.read_text(encoding="utf8"))
                    for f in (a.p210,a.p212,a.p214))
    prev=replay_p213(p210,p212)
    req(prev["verified_original_driver_cases"]==42
        and prev["P210_source_match"]==14
        and prev["P212_source_match"]==28,
        "P210/P212 actual original Creative baseline source replay corrupted")
    total,new_base,direct=verify_p214(p214)
    mutations=(
        lambda v:v["cases"][4].update({"creative_dcysus_first_write":"0x3F27"}),
        lambda v:v["cases"][4].update({"creative_dcysus_release_write":"0x8026"}),
        lambda v:v.update({"source_run":0}),
        lambda v:v.update({"source_artifact_id":0}),
        lambda v:v.update({"source_derived_sf2_sha256":"0"*64}),
        lambda v:v["cases"][6].update({"program":101}),
        lambda v:v["cases"][6].update({"instrument_sustain_base":500}),
        lambda v:v["cases"][6].update({"requested_sustain":750}),
        lambda v:v["cases"][6].update({"preset_sustain_delta":0}),
        lambda v:v["cases"].pop()
    )
    for mutate in mutations:
        sample=deepcopy(p214)
        mutate(sample)
        try:verify_p214(sample)
        except ValueError:pass
        else:raise AssertionError("malformed Creative evidence incorrectly accepted")
    result={
        "schema":"P214-Creative-70-actual-driver-note-case-immutable-replay-v1",
        "sources":[42722686808,42727927825,42737751948],
        "source_artifact_ids":{"p214":13727998644},
        "actual_original_driver_cases_replayed":42+total,
        "p210_matches":14,"p212_matches":28,"p214_matches":total,
        "p214_new_instrument_base_matches":new_base,
        "p214_one_stage_model_matches":direct,
        "p214_cases_discriminating_between_one_and_two_stage":total-direct,
        "deliberate_corruptions_rejected":len(mutations),
        "another_original_driver_execution":False,
        "original_driver_and_audio_media_redistributed":False,
        "full_VXD_call_graph_tested":False,
        "physical_EMU8000_and_DAW_tests":"NOT RUN",
        "product_DSP_modified":False,
        "release":"NO-GO"
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("P214 archived original Creative Win95 70/70 cases: P210 14/14, P212 28/28, P214 28/28, 21/21 unseen instrument bases")
    print("P214 12/28 source-base cases discriminate actual two-stage path from single-stage formula; ten negative original-source mutations rejected")
    print("No new original driver invocation; product VST3, physical hardware and DAW remain NOT RUN")

if __name__=="__main__":main()
