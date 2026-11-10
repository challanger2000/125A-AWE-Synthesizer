#!/usr/bin/env python3
"""P217 independent actual native 125A EMU8000 filter register capture.

This is NOT an original Creative Win95 trace, nor a physical AWE64 recording.
Capture first, then compare it to immutable independently captured original
Win95 Creative data. The two observations must not be conflated.
"""
import argparse,hashlib,json
from pathlib import Path
from p89_compare_voice_registers import native_trace
from p217_clone_filter_matrix import SCHEMA,CASES,require

EXPECTED_SF2_SHA256="89792cb61712c1a33a5bead1ff4318005e293dbfd1443ac148c3a46d85ff0b61"
P216_SOURCE_SHA="65ffbc909867ee54e2a2819990844fa8e3bf6bc6"
REGS=("IFATN","CCCA_LO","CCCA_HI","PEFE","FMMOD")
def values(trace,name):
    a=[w for voice,reg,w in trace if reg==name]
    require(bool(a) and len(a)<=4,"unavailable native register "+name)
    return a
def capture(bank,manifest,traces):
    require(manifest.get("schema")==SCHEMA and
            manifest.get("derived_sf2_sha256")==EXPECTED_SF2_SHA256,
            "not exact original source 28-case SF2")
    require(hashlib.sha256(bank.read_bytes()).hexdigest()==EXPECTED_SF2_SHA256,
            "actual native bank not identical to original planned bank")
    matrix=manifest["matrix"]
    require(len(matrix)==28 and
        [(x["program"],x["generator_operator"],x["requested_effective_value"]) for x in matrix]
        ==[(p,o,v) for p,o,name,v,d in CASES],
        "native filter corpus altered")
    cases=[]
    for row in matrix:
        program=row["program"]
        path=traces/f"B0_P{program}_N59_native-port-write.trace"
        seq=native_trace(path)
        require(len({voice for voice,_,_ in seq})==1,"native voice overlap")
        pairs={name:values(seq,name) for name in REGS}
        cases.append({
          "program":program,
          "generator_operator":row["generator_operator"],
          "generator_name":row["generator_name"],
          "requested_effective_value":row["requested_effective_value"],
          "preset_additive_offset":row["preset_additive_offset"],
          "native_register_series":{k:[f"0x{z:04X}" for z in pairs[k]] for k in REGS},
          "native_cutoff_high_byte":pairs["IFATN"][0]>>8,
          # The INITIAL CCCA_HI write programs Q=0; the final one
          # carries the real resonance. Retain BOTH raw writes.
          "native_Q_high_nibble":pairs["CCCA_HI"][-1]>>12,
          "native_EG1_filter_depth_byte":pairs["PEFE"][0]&255,
          "native_LFO_filter_depth_byte":pairs["FMMOD"][0]&255,
          "native_active_voices":1})
    return {"schema":"P217-actual-native-125A-filter-register-28-v1",
            "pinned_125A_product_commit":P216_SOURCE_SHA,
            "source_derived_sf2_sha256":EXPECTED_SF2_SHA256,
            "native_86box_emu8000_actual_voice_playback":True,
            "original_Creative_Win95_guest_driver_executed_here":False,
            "original_Creative_oracle_comparison":"NOT RUN",
            "physical_original_Creative_hardware":"NOT RUN",
            "actual_Studio_One_ASIO":"NOT RUN",
            "cases":cases,"product_DSP_modified":False,"release":"NO-GO"}
def selftest():
    require(len(CASES)==28 and {x[1] for x in CASES}=={8,9,10,11},
            "native reference corpus")
    print("P217 native capture selftest PASS – comparison will be independent of original Creative Win95 capture")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--sf2",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--trace-dir",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args();selftest()
    if a.self_test and not a.sf2:return
    require(all((a.sf2,a.manifest,a.trace_dir,a.out)),"missing real PCM/voice source")
    r=capture(a.sf2,json.loads(a.manifest.read_text()),a.trace_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(r,indent=2)+"\n")
    print("P217 native original-source same-bank actual 125A 86Box register traces",len(r["cases"]),"/28 CAPTURED; original Creative match NOT YET EVALUATED")
if __name__=="__main__":main()
