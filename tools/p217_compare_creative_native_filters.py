#!/usr/bin/env python3
"""P217 compare ACTUAL original Creative Win95 registers with ACTUAL P216 86Box.

Hard-rule: compare stored register observations, never predict an expected
Creative value from 125A's current formulas or rewrite the original oracle.
The original Creative guest run and the native 125A run are independent.
"""
from __future__ import annotations
import argparse,json
from copy import deepcopy
from pathlib import Path
from p217_clone_filter_matrix import CASES

SOURCE_SHA="89792cb61712c1a33a5bead1ff4318005e293dbfd1443ac148c3a46d85ff0b61"
VXD_SHA="d343f2428ab3e593c9e42a668cf521b7801e1239792eaf7f2b11b5f179bc7c9a"
P216_SHA="50dbd6713736b9c60bb33a3a5c737e57b926fd64"
ORIGINAL_SCHEMA="P217-genuine-original-Win95-Creative-SF2-filter-register-28-v1"
NATIVE_SCHEMA="P217-actual-native-125A-filter-register-28-v1"
REGS=("IFATN","CCCA_LO","CCCA_HI","PEFE","FMMOD")
REGION={
 "initialFilterFc":("IFATN",lambda x:x>>8),
 "initialFilterQ":("CCCA_HI",lambda x:x>>12),
 "modEnvToFilterFc":("PEFE",lambda x:x&255),
 "modLfoToFilterFc":("FMMOD",lambda x:x&255)}
def require(ok,msg):
    if not ok:raise ValueError("P217 independent ORIGINAL CREATIVE/native FILTER EVIDENCE INVALID: "+msg)
def fields(original,native):
    require(original.get("schema")==ORIGINAL_SCHEMA and
       original.get("authentic_Creative_Win95_WinMM_86Box_EMU8000_executed") is True and
       original.get("original_win95_creative_register_windows")==28 and
       original.get("original_Creative_driver_sha256")==VXD_SHA and
       original.get("derived_SF2_sha256")==SOURCE_SHA,
       "not genuine original Creative Win95 guest oracle")
    require(native.get("schema")==NATIVE_SCHEMA and
       native.get("native_86box_emu8000_actual_voice_playback") is True and
       native.get("pinned_125A_product_commit")==P216_SHA and
       native.get("source_derived_sf2_sha256")==SOURCE_SHA and
       native.get("original_Creative_Win95_guest_driver_executed_here") is False,
       "not independently observed actual P216 native 86Box playback")
    a,b=original.get("cases",[]),native.get("cases",[])
    require(len(a)==len(b)==len(CASES)==28,"not complete 28 independent source observations")
    out=[]
    for expected,x,y in zip(CASES,a,b):
        program,op,label,requested,default=expected
        require(x.get("program")==y.get("program")==program and
           x.get("generator_operator")==y.get("generator_operator")==op and
           x.get("generator_name")==y.get("generator_name")==label and
           x.get("requested_effective_value")==y.get("requested_effective_value")==requested and
           x.get("preset_additive_offset")==y.get("preset_additive_offset"),
           "mismatched original/native SF2 program, generator or input value")
        require(x.get("original_active_voice_count")==1 and
           y.get("native_active_voices")==1,"source-voice overlap or native silence")
        o=x.get("original_creative_register_series")
        n=y.get("native_register_series")
        require(isinstance(o,dict) and isinstance(n,dict) and
                set(o)==set(n)==set(REGS),"incomplete original/native register set")
        decoded={}
        for k in REGS:
            require(isinstance(o[k],list) and isinstance(n[k],list) and
               1<=len(o[k])<=4 and 1<=len(n[k])<=4,"missing/malformed register histories")
            def read(v):
                require(type(v) is str and len(v)==6 and v.startswith("0x"),
                        "invalid register hex format")
                z=int(v,16)
                require(0<=z<=65535,"invalid ISA register word")
                return z
            decoded[k]=(tuple(read(v) for v in o[k]),tuple(read(v) for v in n[k]))
        out.append((program,label,requested,decoded))
    return out
def compare(o,n):
    rows=fields(o,n)
    cases=[];results={}
    for program,label,requested,d in rows:
        reg,decode=REGION[label]
        orig,native=d[reg]
        # CCCA_HI is written twice: preliminary Q=0, then FINAL effective
        # filter resonance. Reading only the first gives a false zero-Q
        # report despite actual native Q=8 etc. Compare LAST captured write.
        oi=-1 if label=="initialFilterQ" else 0
        original_value,native_value=decode(orig[oi]),decode(native[oi])
        cases.append({
           "program":program,"generator_name":label,"requested_effective_value":requested,
           "original_Creative_decoded_register":original_value,
           "P216_native_decoded_register":native_value,
           "target_axis_exact":original_value==native_value,
           "target_register_effective_write_exact":orig[oi]==native[oi],
           "target_register_complete_write_series_exact":orig==native,
           "all_five_register_series_exact":all(x==y for x,y in d.values()),
           "per_register_full_series_equal":{k:v[0]==v[1] for k,v in d.items()},
           "original_Creative_raw_registers":{k:[f"0x{x:04X}" for x in v[0]] for k,v in d.items()},
           "P216_native_raw_registers":{k:[f"0x{x:04X}" for x in v[1]] for k,v in d.items()},
        })
    for label in REGION:
        group=[c for c in cases if c["generator_name"]==label]
        results[label]={"tested_original_source_cases":len(group),
                        "target_axis_correct":sum(c["target_axis_exact"] for c in group),
                        "full_target_register_effective_write_exact":sum(c["target_register_effective_write_exact"] for c in group),
                        "full_target_register_series_exact":sum(c["target_register_complete_write_series_exact"] for c in group),
                        "entire_five_register_series_exact":sum(c["all_five_register_series_exact"] for c in group),
                        "original_Creative_register_values":[c["original_Creative_decoded_register"] for c in group],
                        "P216_native_register_values":[c["P216_native_decoded_register"] for c in group],
                        "status":"PASS" if all(c["target_axis_exact"] for c in group) else "FAIL"}
    return {"schema":"P217-independent-28-real-Creative-vs-real-P216-filter-register-parity-v1",
            "source_soundfont_sha256":SOURCE_SHA,
            "original_Creative_SBAWE_VXD_sha256":VXD_SHA,
            "P216_exact_product_source_sha":P216_SHA,
            "product_DSP_modified":False,
            "genuine_Creative_original_driver_executed_in_original_capture":True,
            "genuine_original_Creative_AWE64_physical_hardware_tested":False,
            "frequency_response_and_analog_filter_parity_tested":False,
            "filter_eg1_lfo_timing_and_adsr_all_combinations_tested":False,
            "Studio_One_ASIO":"NOT RUN",
            "release":"NO-GO",
            "per_filter_domain":results,
            "total_target_register_matches":sum(c["target_axis_exact"] for c in cases),
            "total_five_register_complete_series_matches":sum(c["all_five_register_series_exact"] for c in cases),
            "cases":cases}

def selftest():
    # These made-up values are ONLY mutation-counterexample fixtures, never
    # uploaded as original Creative measurements or accepted as hardware data.
    A=[];B=[]
    for program,op,label,target,default in CASES:
        row=dict(program=program,generator_operator=op,generator_name=label,
                 requested_effective_value=target,preset_additive_offset=target-default,
                 original_active_voice_count=1,native_active_voices=1)
        raw={k:["0x0020"] for k in REGS}
        # Reproduce the genuine double CCCA programming order: preliminary
        # Q=0, final Q=8. This is NOT a Creative hardware observation.
        raw["CCCA_HI"]=["0x0020","0x8020"]
        A.append({**row,"original_creative_register_series":deepcopy(raw)})
        B.append({**row,"native_register_series":deepcopy(raw)})
    original=dict(schema=ORIGINAL_SCHEMA,
       authentic_Creative_Win95_WinMM_86Box_EMU8000_executed=True,
       original_win95_creative_register_windows=28,
       original_Creative_driver_sha256=VXD_SHA,derived_SF2_sha256=SOURCE_SHA,cases=A)
    native=dict(schema=NATIVE_SCHEMA,
       native_86box_emu8000_actual_voice_playback=True,
       pinned_125A_product_commit=P216_SHA,
       source_derived_sf2_sha256=SOURCE_SHA,
       original_Creative_Win95_guest_driver_executed_here=False,cases=B)
    require(len(fields(original,native))==28,"valid synthetic selftest structure")
    muts=(
       lambda a,b:a.update({"authentic_Creative_Win95_WinMM_86Box_EMU8000_executed":False}),
       lambda a,b:b.update({"source_derived_sf2_sha256":"0"*64}),
       lambda a,b:a["cases"][13].update({"program":110}),
       lambda a,b:b["cases"][6].update({"requested_effective_value":9999}),
       lambda a,b:a["cases"][0]["original_creative_register_series"].pop("IFATN"),
       lambda a,b:b["cases"][7].update({"native_active_voices":2}),
       lambda a,b:a["cases"].pop(),
    )
    for fn in muts:
        a,b=deepcopy((original,native))
        fn(a,b)
        try:fields(a,b)
        except ValueError:continue
        raise AssertionError("P217 invalid source evidence incorrectly accepted")
    c=deepcopy(native)
    c["cases"][0]["native_register_series"]["IFATN"][0]="0xFF20"
    result=compare(original,c)
    require(result["total_target_register_matches"]==27 and
        result["per_filter_domain"]["initialFilterFc"]["status"]=="FAIL",
        "false-green mutant: changed native cutoff incorrectly matched original")
    q=deepcopy(native)
    q["cases"][11]["native_register_series"]["CCCA_HI"][-1]="0x0020"
    qr=compare(original,q)
    require(qr["total_target_register_matches"]==27 and
        qr["per_filter_domain"]["initialFilterQ"]["status"]=="FAIL" and
        qr["per_filter_domain"]["initialFilterQ"]["P216_native_register_values"][4]==0,
        "false-green mutant: ignoring FINAL Q register write")
    print("P217 independent parity comparator selftest PASS: seven source mutations rejected, cutoff and final-Q mutants rejected")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--creative",type=Path)
    p.add_argument("--native",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    selftest()
    if a.self_test and not a.creative:return
    require(a.creative and a.native and a.out,
            "original Creative numerical capture and independent native P216 capture required")
    result=compare(json.loads(a.creative.read_text()),json.loads(a.native.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    for label,v in result["per_filter_domain"].items():
        print("P217 actual original Creative vs actual P216",label,":",
              v["target_axis_correct"],"/",v["tested_original_source_cases"],
              "status",v["status"],
              "original",v["original_Creative_register_values"],
              "native",v["P216_native_register_values"])
    print("P217 overall decoded target filter register fidelity:",
          result["total_target_register_matches"],"/28;",
          "full 5-register series identical",result["total_five_register_complete_series_matches"],"/28")
    print("Hardware filter response, envelope curves, physical output, DAW remain NOT VERIFIED")
    if any(v["status"]=="FAIL" for v in result["per_filter_domain"].values()):
        raise SystemExit("P217 FAIL: measured original Creative filter register mismatch (saved exact diagnostics)")
if __name__=="__main__":main()
