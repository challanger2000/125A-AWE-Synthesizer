#!/usr/bin/env python3
"""P220 frozen authentic Synth 512 Bank 77-program MIDI/audio capture contract.

Reuses P80 source inspector; never stores/distributes SF2, samples or ROM.
This file generates only a *plan* and has no claim of original driver load.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from p80_full_sf2_inventory import inventory,PROGRAMS
BANK_SHA="d5b99ec38fddf59f53f66b90921e170d207bf3bbd73960f6e4175c39ef68349b"
SCHEMA="125a-awe-sf2-77-audio-contract-v1"
def plan(bank):
    raw=Path(bank).read_bytes()
    source_sha=hashlib.sha256(raw).hexdigest()
    if source_sha!=BANK_SHA:
        raise ValueError("P220 NOT THE OWNER'S PINNED ORIGINAL 77-PRESET SF2")
    checked=inventory(raw)
    presets=checked["presets"]
    if [p["program"] for p in presets]!=sorted(PROGRAMS):
        raise ValueError("P220 original MIDI bank-order mapping invalid")
    cases=[]
    for item in presets:
        p=item["program"]
        for mode,note,velocity,cc in (
            ("DRY",48,64,{"1":0,"7":100,"11":127,"91":0,"93":0}),
            ("MODFX",72,120,{"1":96,"7":100,"11":127,"91":48,"93":32}),
        ):
            ident=f"P{p:03d}-{mode}"
            cases.append({
                "id":ident,"program":p,"preset_name":item["name"],
                "variant":mode,"channel":0,"user_bank":1,
                "note":note,"velocity":velocity,
                "controllers":cc,"note_off_ms":1000,"record_ms":3000,
                "creative_wav":ident+".wav","vst3_wav":ident+".wav",
                "midi_event_order":["CC0_bank1","CC7","CC11","CC1","CC91","CC93",
                                    "PROGRAM_CHANGE","NOTE_ON","NOTE_OFF"],
                "expected_audio_status":"MUST_BE_MEASURED_NOT_ASSUMED"})
    return {
        "schema":SCHEMA,"private_sf2_sha256":source_sha,
        "private_original_sf2_bytes":len(raw),"presets":presets,
        "programs":[x["program"] for x in presets],
        "missing_midi_program":63,"scenarios":cases,
        "independent_detail_gates":{"per_program":{
            str(p):{k:{"status":"NOT TESTED"} for k in (
              "amplitude_adsr","filter_sweeps","loop_seams",
              "dry_wet_reverb_chorus","program_recall_and_reload")}
            for p in sorted(PROGRAMS)}},
        "creative_original_driver_capture":"NOT RUN",
        "real_windows_vst3_capture":"NOT RUN",
        "physical_creative_awe64_hardware":"NOT RUN",
        "release_approved":False,
        "source_soundfont_bytes_in_plan":False,
        "policy":"Original Creative Win95 driver, emulated EMU8000 and actual VST3 are separate systems"
    }
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sf2",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    obj=plan(a.sf2)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("P220 authentic owner SF2 corpus:",len(obj["presets"]),
          "presets",len(obj["scenarios"]),"deterministic dual-backend trial pairs; original driver PCM NOT TESTED")
if __name__=="__main__":main()
