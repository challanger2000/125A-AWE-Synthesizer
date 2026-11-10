#!/usr/bin/env python3
"""Actual Win95 original SBAWE.VXD vs current native chip SustainVolEnv 4x7 grid.

Never treat predicted source-derived values as original observed values:
real Win95 original-driver register I/O is the only ground truth.
"""
import argparse,hashlib,json,sys
from pathlib import Path

from creative_win95_vol_sustain_two_stage import (
    CASES,BASES,TARGETS,SCHEMA,require
)

def trunc0(n,d):return (1 if n>=0 else -1)*(abs(n)//d)
def T(n):return 127+trunc0(-127*n,1000)
def clamp(n):return min(127,max(0,n))

def source_checks(manifest, guest,verify):
    require(manifest.get("schema")==SCHEMA and
            manifest.get("original_audio_pcm_byte_identical") is True and
            manifest.get("original_six_presets_preserved") is True and
            manifest.get("original_25_instruments_preserved") is True and
            manifest.get("original_44_sample_records_preserved") is True and
            manifest.get("instrument_bases")==list(BASES) and
            manifest.get("target_values")==list(TARGETS),
            "Creative accepted original sample provenance lost")
    rows=manifest.get("cases",[])
    require(len(rows)==28 and
            [(x.get("program"),x.get("instrument_sustain_base"),
              x.get("requested_total_volume_sustain")) for x in rows]==list(CASES),
            "not original precisely crossed 28 instrument/preset settings")
    require(all(x.get("preset_sustain_delta")==
                    x["requested_total_volume_sustain"]-x["instrument_sustain_base"]
                and x.get("volume_sustain_generator_id")==37 and
                x.get("note")==59 and x.get("velocity")==100 and
                x.get("original_sample_id")==43 for x in rows),
            "not the original sample43 note59 one-voice additive generator plan")
    require(verify.get("agent_launched_in_actual_win95") is True and
            verify.get("original_creative_winmm_endpoint_selected") is True and
            verify.get("original_creative_com1_ready") is True and
            verify.get("creatives_midi_short_messages_delivered",0)>=112 and
            verify.get("audio_observed") is True and
            verify.get("p84_universal_sf2_test") is True and
            not verify.get("win95_agent_error"),
            "NOT verified original Windows95 SBAWE.VXD sample playback")
    require(guest.get("hardware")=="sbawe64_gold" and
            guest.get("sample_ram_kib")==28672 and
            guest.get("p75_private_sample_upload_plausible") is True and
            guest.get("p75_private_sample_upload_write_words",0)>=
                guest.get("p75_private_sample_upload_minimum_words",1),
            "wrong Creative test card/RAM or SoundFont not uploaded")
    trial=guest.get("p64_original_win95_midi",{})
    windows=trial.get("p214_original_creative_register_windows",[])
    require(trial.get("p214_real_win95_driver_sweep") is True and
            len(windows)==28 and
            [x.get("program") for x in windows]==list(range(100,128)),
            "no original 28 note window traces")
    end=-1
    for window in windows:
        start,stop=window.get("start_row"),window.get("end_row")
        require(type(start) is int and type(stop) is int and start>=end and
                stop>start and window.get("window_isolated") is True and
                window.get("note")==59 and window.get("velocity")==100,
                "overlapping/non-note/wrong-velocity original driver trace")
        end=stop
    return rows,windows

def self_test():
    require(T(0)==127 and T(250)==96 and T(500)==64 and T(1000)==0,
            "integer conversion reference drift")
    require(T(-250)==158 and T(250)==96,
            "signed division for negative preset delta must truncate toward zero")
    assert clamp(T(500)+T(500)-127)==1 and T(1000)==0
    for bad in (CASES[:-1],CASES[::-1]):
        try:require(len(bad)==28 and list(bad)==list(CASES),
                    "wrong crossed input matrix")
        except ValueError:continue
        raise AssertionError("deliberate damaged 4x7 program matrix accepted")
    print("CREATIVE_VOLUME_SUSTAIN_TWO_STAGE_COMPARATOR_SELF_TEST_PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    for name in ("manifest","guest_report","guest_verification","creative_csv",
                 "native_dir","derived_sf2","out","historic_tools"):
        p.add_argument("--"+name.replace("_","-"),type=Path)
    a=p.parse_args()
    self_test()
    if a.self_test and not a.manifest:return
    require(all(getattr(a,k) for k in
        ("manifest","guest_report","guest_verification","creative_csv",
         "native_dir","derived_sf2","out","historic_tools")),
         "real original Win95 driver data and native traces required")
    sys.path.insert(0,str(a.historic_tools.resolve()))
    from p89_compare_voice_registers import original_csv,native_trace
    from creative_win95_sf2_envelope_compare import filter_words
    manifest=json.loads(a.manifest.read_text())
    guest=json.loads(a.guest_report.read_text())
    verify=json.loads(a.guest_verification.read_text())
    cases,windows=source_checks(manifest,guest,verify)
    require(hashlib.sha256(a.derived_sf2.read_bytes()).hexdigest()==
            manifest["derived_sf2_sha256"],"original Creative uploaded the wrong bank bytes")
    results=[]
    for row,window in zip(cases,windows):
        program=row["program"]
        original=original_csv(a.creative_csv,window["start_row"],window["end_row"])
        trace=a.native_dir/f"B0_P{program}_N59_native-port-write.trace"
        require(trace.is_file(),"missing real EMU8000 native chip port-write trace")
        native=native_trace(trace)
        orig=filter_words(original,"DCYSUSV")
        ours=filter_words(native,"DCYSUSV")
        orig_hold=filter_words(original,"ATKHLD")
        native_hold=filter_words(native,"ATKHLD")
        require(orig_hold==native_hold,"hold control mismatch/voice contamination, invalid cross comparison")
        base=row["instrument_sustain_base"];total=row["requested_total_volume_sustain"]
        delta=total-base
        direct=clamp(T(total))
        two_stage=clamp(T(base)+T(delta)-127)
        results.append({"program":program,"instrument_value":base,
            "preset_delta":delta,"merged_value":total,
            "measured_original_Creative_DCYSUSV_high":orig,
            "measured_current_native_DCYSUSV_high":ours,
            "predicted_direct_merged_conversion":direct,
            "predicted_two_stage_instrument_plus_preset":two_stage,
            "native_exact":orig==ours,
            "original_matches_direct":orig==direct,
            "original_matches_two_stage":orig==two_stage,
            "original_modhold_control":orig_hold})
    require(len(results)==28 and
            [(r["program"],r["instrument_value"],r["merged_value"]) for r in results]
            ==list(CASES),"28 measured original value pairs not complete")
    exact=sum(x["native_exact"] for x in results)
    direct=sum(x["original_matches_direct"] for x in results)
    two_stage=sum(x["original_matches_two_stage"] for x in results)
    out={"schema":"125A-actual-Creative-Win95-vol-sustain-crossed-28-oracle",
         "original_Creative_driver_and_44_sample_upload_executed":True,
         "original_soundfont_sha256":manifest["derived_sf2_sha256"],
         "original_public_source_git_blob":manifest["public_source_git_blob"],
         "original_driver_original_soundfont_presets_preserved":True,
         "actual_Win95_Creative_windows":len(windows),
         "note":59,"velocity":100,
         "actual_native_register_parity_cases":exact,
         "original_matches_one_stage_merged_cases":direct,
         "original_matches_two_stage_source_cases":two_stage,
         "cases":results,
         "original_media_uploaded_to_public_repo":False,
         "physical_hardware":False,
         "owner_VST3_daw_validation":False,
         "release":"BLOCKED"}
    require(not a.out.exists(),"refuse overwrite original observed values")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=2)+"\n")
    print("REAL_CREATIVE_WIN95_VOLUME_SUSTAIN_28_ORIGINAL_CASES",
          "native_matches",exact,"of28",
          "one_stage",direct,"two_stage",two_stage)
    for x in results:
        if not x["native_exact"]:
            print("ACTUAL_CREATIVE_VOLUME_SUSTAIN_MISMATCH",
                  json.dumps(x,sort_keys=True))
if __name__=="__main__":main()
