#!/usr/bin/env python3
"""Compare genuine original Win95 SBAWE.VXD against CURRENT 125A native 86Box.

No hardcoded original register EXPECTATION. Both port-write traces must exist
and be independently captured for the very same verified, source-derived SF2.
Only parsed numerical diagnostics, NEVER original ROM/SF2/WAV/guest image,
are written into the public artifact.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from creative_win95_sf2_envelope_sweep import PROGRAMS, SCHEMA, VOL_VALUES, HOLD_VALUES, require

def read_metadata(manifest, guest, proof):
    require(manifest.get("schema")==SCHEMA and
            manifest.get("original_pcm_byte_identical") is True and
            manifest.get("original_presets_instrument_sample_tables_unchanged") is True,
            "untrusted original-source-derived bank provenance")
    cases=manifest.get("cases",[])
    require(len(cases)==28 and [c.get("program") for c in cases]==list(PROGRAMS),
            "28 user-value matrix not actually present")
    require([c.get("generator_value") for c in cases[:14]]==list(VOL_VALUES) and
            [c.get("generator_value") for c in cases[14:]]==list(HOLD_VALUES),
            "real SF2 input value series was permuted")
    require(proof.get("agent_launched_in_actual_win95") is True and
            proof.get("original_creative_winmm_endpoint_selected") is True and
            proof.get("original_creative_com1_ready") is True and
            proof.get("audio_observed") is True and
            proof.get("p84_universal_sf2_test") is True and
            proof.get("creatives_midi_short_messages_delivered",0)>=112,
            "original Windows 95 Creative physical-driver route NOT proven")
    require(guest.get("hardware")=="sbawe64_gold" and
            guest.get("sample_ram_kib")==28672 and
            guest.get("p75_private_sample_upload_plausible") is True and
            guest.get("p75_private_sample_upload_write_words",0)>=
                guest.get("p75_private_sample_upload_minimum_words",1),
            "guest not real Creative, wrong card or original SF2 not uploaded")
    trial=guest.get("p64_original_win95_midi",{})
    windows=trial.get("p214_original_creative_register_windows",[])
    require(trial.get("p214_real_win95_driver_sweep") is True and
            len(windows)==28 and [w.get("program") for w in windows]==list(PROGRAMS),
            "Win95 driver did not play 28 real isolated programs")
    last_end=-1
    for w in windows:
        start,end=w.get("start_row"),w.get("end_row")
        require(type(start) is int and type(end) is int and
                0<=start<end and start>=last_end and
                w.get("window_isolated") is True and
                w.get("note")==59 and w.get("velocity")==100,
                "original Creative note window wrong or overlapping")
        last_end=end
    return cases,windows

def filter_words(sequence,register):
    # The first actual full-value write during an active note should not be
    # mistaken for an init 0x00FF or a note-off 0x80xx release write.
    voices={voice for voice,name,value in sequence
            if name in ("ATKHLD","DCYSUSV","DCYSUS","CCCA_HI")}
    require(len(voices)==1,"source sample43 note59 did not start one chip voice")
    parts=[v for voice,name,v in sequence if name==register]
    require(parts,"missing actual "+register+" chip register data")
    if register=="DCYSUSV":
        active=[v for v in parts if (v & 0x8000)==0 and (v & 0xff)!=0xff]
        require(active,"no actual non-init/release DCYSUSV register during note")
        return active[0]>>8
    if register=="ATKHLD":
        require(len(parts)>=1,"ATKHLD absent")
        return (parts[0]>>8)&0x7f
    raise ValueError("unsupported register")

def main():
    ap=argparse.ArgumentParser()
    for k in ("manifest","guest_report","guest_verification",
              "original_csv","native_dir","derived_sf2","out","historic_tools"):
        ap.add_argument("--"+k.replace("_","-"),type=Path,required=True)
    args=ap.parse_args()
    sys.path.insert(0,str(args.historic_tools.resolve()))
    from p89_compare_voice_registers import original_csv,native_trace
    manifest=json.loads(args.manifest.read_text())
    guest=json.loads(args.guest_report.read_text())
    proof=json.loads(args.guest_verification.read_text())
    cases,windows=read_metadata(manifest,guest,proof)
    require(hashlib.sha256(args.derived_sf2.read_bytes()).hexdigest()==
            manifest["derived_sha256"],"the original driver bank bytes have changed")
    observations=[]
    parity=0
    examples=[]
    for case,window in zip(cases,windows):
        program=case["program"]
        original=original_csv(args.original_csv,window["start_row"],window["end_row"])
        trace=args.native_dir/f"B0_P{program}_N59_native-port-write.trace"
        require(trace.is_file(),"missing current engine real-EMU8000 trace "+str(trace))
        native=native_trace(trace)
        orig_hold=filter_words(original,"ATKHLD")
        orig_vol=filter_words(original,"DCYSUSV")
        our_hold=filter_words(native,"ATKHLD")
        our_vol=filter_words(native,"DCYSUSV")
        both=(orig_hold==our_hold and orig_vol==our_vol)
        parity+=both
        observations.append({"program":program,"mode":case["mode"],
           "sf2_generator_input":case["generator_value"],
           "original_creative_ATKHLD_hold":orig_hold,
           "current_125a_ATKHLD_hold":our_hold,
           "original_creative_DCYSUSV_sustain":orig_vol,
           "current_125a_DCYSUSV_sustain":our_vol,
           "both_expected_registers_match":both})
        if not both:
            examples.append({"program":program,"generator":case["generator_value"],
                             "mode":case["mode"],
                             "original_hold":orig_hold,"native_hold":our_hold,
                             "original_vol":orig_vol,"native_vol":our_vol})
    require(len(observations)==28,"incomplete actual original driver note coverage")
    require(len({x["program"] for x in observations})==28,
            "duplicate original driver program substituted")
    result={"schema":"125a-Creative-Win95-genuine-generator-sweep-parity-v1",
        "original_Creative_Win95_SBAWE_VXD_and_real_sample_upload":True,
        "original_MIDI_note":59,"original_velocity":100,
        "original_Creative_emulated_board":"awe64_gold",
        "original_bank_sha256":manifest["derived_sha256"],
        "public_source_git_blob":manifest["public_accepted_source_git_blob"],
        "actual_original_driver_note_windows":len(windows),
        "original_Creative_voice_register_parity_cases":parity,
        "instrument_generator_input_cases":len(observations),
        "volume_sustain_cases":len(VOL_VALUES),
        "modulation_hold_cases":len(HOLD_VALUES),
        "all_matches":parity==len(observations),
        "cases":observations,
        "first_mismatches":examples[:10],
        "original_licensed_soundfont_published":False,
        "physical_soundcard_test":False,
        "Windows_VST3_owner_daw_test":False,
        "release":"BLOCKED"}
    require(not args.out.exists(),"do not overwrite real original measurements")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n")
    print("ORIGINAL_CREATIVE_WIN95_GENERATOR_SWEEP_EVIDENCE",
          "cases",len(observations),"exact",parity,
          "not_equal",len(observations)-parity,
          "original_driver=YES dry_audio_parity=NOT_ASSERTED")
    for case in examples[:10]:
        print("GENERATOR_SWEEP_MISMATCH",json.dumps(case,sort_keys=True))
if __name__=="__main__":main()
