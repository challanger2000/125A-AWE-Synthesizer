#!/usr/bin/env python3
"""P217: original Creative Win95 SF2 filter register recording oracle.

No modeled native values ever count as original Creative observations.
The source of truth is an actual 1998 Creative SBAWE.VXD Win95 WinMM
endpoint, captured through 86Box as per-source single-note register windows.
Every field and file is independently cross-checked before any outcome.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from copy import deepcopy
from p89_compare_voice_registers import original_csv
from p217_clone_filter_matrix import CASES,SCHEMA as INPUT_SCHEMA
from p210_clone_verified_sf2 import SOURCE_GIT_BLOB

DRIVER_SHA="d343f2428ab3e593c9e42a668cf521b7801e1239792eaf7f2b11b5f179bc7c9a"
ORACLE_SCHEMA="P217-genuine-original-Win95-Creative-SF2-filter-register-28-v1"
REGS=("IFATN","CCCA_LO","CCCA_HI","PEFE","FMMOD")
def require(ok,msg):
    if not ok:raise ValueError("P217 CREATIVE ORIGINAL FILTER SOURCE REJECTED: "+msg)
def validate(manifest,report,verified):
    require(manifest.get("schema")==INPUT_SCHEMA and
       manifest.get("public_original_source_git_blob")==SOURCE_GIT_BLOB and
       manifest.get("original_6_presets_preserved") is True and
       manifest.get("original_25_instruments_preserved") is True and
       manifest.get("original_44_sample_records_preserved") is True and
       manifest.get("original_audio_bytes_identical") is True and
       manifest.get("original_sample_media_published") is False,
       "not the independently identified authentic public source bank")
    matrix=manifest.get("matrix",[])
    require(len(matrix)==28 and len(CASES)==28 and
        [(x.get("program"),x.get("generator_operator"),x.get("requested_effective_value")) for x in matrix]
           ==[(p,op,v) for p,op,lab,v,d in CASES],"test matrix differs from frozen 4×7 model")
    require(all(x.get("preset_additive_offset")==
          x.get("requested_effective_value")-x.get("instrument_base_value") and
          x.get("reference_sample_id")==43 and x.get("midi_note")==59 and
          x.get("velocity")==100 and x.get("no_original_Creative_register_values_embedded") is True
          for x in matrix),"preset sum, note, source sample or independence violated")
    require(report.get("hardware")=="sbawe64_gold" and report.get("sample_ram_kib")==28672 and
       report.get("p84_universal_sf2_test") is True and
       report.get("p75_private_sample_upload_plausible") is True and
       report.get("p75_private_sample_upload_write_words",0)>=
         report.get("p75_private_sample_upload_minimum_words",1),
       "not actual original loaded SoundFont under AWE64 Gold 28MiB")
    require(verified.get("agent_launched_in_actual_win95") is True and
       verified.get("original_creative_winmm_endpoint_selected") is True and
       verified.get("original_creative_com1_ready") is True and
       not verified.get("win95_agent_error") and
       verified.get("creatives_midi_short_messages_delivered",0)>=112 and
       verified.get("audio_observed") is True and
       verified.get("p84_universal_sf2_test") is True,
       "no genuine Win95 Creative MIDI/PCM evidence")
    t=report.get("p64_original_win95_midi",{})
    require(t.get("p217_real_win95_filter_sweep") is True and
        not t.get("p214_real_win95_driver_sweep") and
        not t.get("p212_real_win95_driver_sweep") and
        not t.get("p210_real_win95_driver_sweep") and
        t.get("p74_uart_frames_injected",0)>=112,
        "not new P217 original Win95 filter sweep")
    windows=t.get("p217_original_creative_filter_windows",[])
    require(len(windows)==28 and [x.get("program") for x in windows]==list(range(100,128)),
        "original note windows not 28 independent ordered programs")
    last=-1
    for w in windows:
        start,end=w.get("start_row"),w.get("end_row")
        require(type(start) is int and type(end) is int and
            start>=last and end>start and
            w.get("window_isolated") is True and w.get("note")==59 and
            w.get("velocity")==100,
            "contaminated or overlapping actual Creative register trace")
        last=end
    return windows

def selftest():
    matrix=[dict(program=p,generator_operator=op,requested_effective_value=v,
         instrument_base_value=d,preset_additive_offset=v-d,reference_sample_id=43,
         midi_note=59,velocity=100,no_original_Creative_register_values_embedded=True)
         for p,op,_,v,d in CASES]
    manifest=dict(schema=INPUT_SCHEMA,public_original_source_git_blob=SOURCE_GIT_BLOB,
      original_6_presets_preserved=True,original_25_instruments_preserved=True,
      original_44_sample_records_preserved=True,original_audio_bytes_identical=True,
      original_sample_media_published=False,matrix=matrix)
    report=dict(hardware="sbawe64_gold",sample_ram_kib=28672,
       p84_universal_sf2_test=True,p75_private_sample_upload_plausible=True,
       p75_private_sample_upload_write_words=120,p75_private_sample_upload_minimum_words=30,
       p64_original_win95_midi=dict(p217_real_win95_filter_sweep=True,
           p74_uart_frames_injected=112,p217_original_creative_filter_windows=[
            dict(program=p,start_row=i*100,end_row=i*100+80,
                 window_isolated=True,note=59,velocity=100)
            for i,(p,_,_,_,_) in enumerate(CASES)]))
    verified=dict(agent_launched_in_actual_win95=True,
        original_creative_winmm_endpoint_selected=True,
        original_creative_com1_ready=True,
        creatives_midi_short_messages_delivered=112,
        audio_observed=True,p84_universal_sf2_test=True,win95_agent_error=False)
    require(len(validate(manifest,report,verified))==28,"good fixture rejected")
    mutants=[
       lambda m,r,v:m["matrix"][0].update({"generator_operator":0}),
       lambda m,r,v:m["matrix"][6].update({"preset_additive_offset":999}),
       lambda m,r,v:m.update({"original_audio_bytes_identical":False}),
       lambda m,r,v:m["matrix"].pop(),
       lambda m,r,v:r["p64_original_win95_midi"].update({"p217_real_win95_filter_sweep":False}),
       lambda m,r,v:r["p64_original_win95_midi"]["p217_original_creative_filter_windows"][13].update({"start_row":0}),
       lambda m,r,v:v.update({"original_creative_winmm_endpoint_selected":False}),
       lambda m,r,v:v.update({"creatives_midi_short_messages_delivered":100}),
       lambda m,r,v:r.update({"p75_private_sample_upload_plausible":False})
    ]
    for fn in mutants:
        m,r,v=deepcopy((manifest,report,verified))
        fn(m,r,v)
        try:validate(m,r,v)
        except ValueError:continue
        raise AssertionError("deliberately damaged P217 source evidence accepted")
    print("P217 comparator selftest PASS: 28 honest Windows Creative cases, nine source/guest/matrix mutations rejected")

def actual_series(seq,key):
    a=[v for _,n,v in seq if n==key]
    require(a and len(a)<=4,"original Creative register absent/malformed "+key)
    return a

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    for a in ("manifest","guest_report","guest_verification","creative_csv","derived_sf2","out"):
        p.add_argument("--"+a.replace("_","-"),dest=a,type=Path)
    args=p.parse_args()
    selftest()
    if args.self_test and not args.manifest:return
    require(all(getattr(args,a) for a in
       ("manifest","guest_report","guest_verification","creative_csv","derived_sf2","out")),
       "complete actual original Win95 Creative report required")
    manifest=json.loads(args.manifest.read_text())
    report=json.loads(args.guest_report.read_text())
    verified=json.loads(args.guest_verification.read_text())
    windows=validate(manifest,report,verified)
    require(hashlib.sha256(args.derived_sf2.read_bytes()).hexdigest()==
            manifest.get("derived_sf2_sha256"),
            "source-derived SF2 actually loaded not identical to manifest")
    cases=[]
    for original_case,w in zip(manifest["matrix"],windows):
        trace=original_csv(args.creative_csv,w["start_row"],w["end_row"])
        require(len({voice for voice,name,value in trace})==1,
                "source original Win95 voice overlap/stealing")
        series={key:actual_series(trace,key) for key in REGS}
        require(all(type(x) is int and 0<=x<=0xffff for rows in series.values() for x in rows),
                "bad original ISA register word")
        # Record both code and actual hardware-ready register output.
        cases.append({"program":w["program"],
            "generator_operator":original_case["generator_operator"],
            "generator_name":original_case["generator_name"],
            "instrument_base_value":original_case["instrument_base_value"],
            "preset_additive_offset":original_case["preset_additive_offset"],
            "requested_effective_value":original_case["requested_effective_value"],
            "original_creative_register_series":{
                key:[f"0x{x:04X}" for x in series[key]] for key in REGS},
            "original_creative_cutoff_high_byte":series["IFATN"][0]>>8,
            "original_creative_filter_Q_high_nibble":series["CCCA_HI"][0]>>12,
            "original_creative_EG1_filter_depth_byte":series["PEFE"][0]&255,
            "original_creative_LFO_filter_depth_byte":series["FMMOD"][0]&255,
            "original_active_voice_count":1})
    effects={}
    register={"initialFilterFc":"original_creative_cutoff_high_byte",
              "initialFilterQ":"original_creative_filter_Q_high_nibble",
              "modEnvToFilterFc":"original_creative_EG1_filter_depth_byte",
              "modLfoToFilterFc":"original_creative_LFO_filter_depth_byte"}
    for name,key in register.items():
        group=[x for x in cases if x["generator_name"]==name]
        effects[name]={"original_tested_values":[x["requested_effective_value"] for x in group],
            "original_distinct_register_outputs":len({x[key] for x in group}),
            "original_outputs":[x[key] for x in group],
            "seven_achieved_nonidentical_register_outputs":len({x[key] for x in group})>=2}
    verdict={"schema":ORACLE_SCHEMA,
       "original_Creative_driver_sha256":DRIVER_SHA,
       "source_public_SF2_git_blob":SOURCE_GIT_BLOB,
       "derived_SF2_sha256":manifest["derived_sf2_sha256"],
       "authentic_Creative_Win95_WinMM_86Box_EMU8000_executed":True,
       "original_win95_creative_register_windows":28,
       "original_registers_recorded_per_case":list(REGS),
       "no_expected_register_values_in_original_source_bank":True,
       "each_dimension_output_diversity":effects,
       "cases":cases,
       "independent_native_125A_comparison":"NOT RUN",
       "physical_Creative_AWE64_filter_audio":"NOT RUN",
       "Studio_One_ASIO":"NOT RUN",
       "P216_product_DSP_modified":False,"release":"NO-GO"}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(verdict,indent=2)+"\n")
    print("P217 ORIGINAL WIN95 CREATIVE FILTER ORACLE CAPTURED",len(cases),"programs")
    for name,info in effects.items():
        print("P217 ACTUAL",name,info["original_outputs"],"distinct",info["original_distinct_register_outputs"])
    if not all(v["seven_achieved_nonidentical_register_outputs"] for v in effects.values()):
        print("P217 FILTER SOURCE WARNING: at least one dimension did not change the original Creative register; preserve negative evidence")
    print("P217 evidence-only original driver run; no native parity, no full silicon/DAW audio fidelity assertion")
if __name__=="__main__":main()
