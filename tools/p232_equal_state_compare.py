#!/usr/bin/env python3
"""P232 same-run original Win95 Creative vs four fixed native ROM/SBK DSP variants.
Hard fail on missing authentic guest proof; audio measurements are never used to
assert equal-state without chip init, register, FX-return, and timing provenance.
The original Win95 reference WAV remains private on the runner.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from p230_rom_sbk_ab import read_wav, compare_pair, align, lag
from p89_compare_voice_registers import native_trace

P=(0,39,80,88,112)
VAR={"A":"measured-fx","B":"no-eq","C":"moog-eq","D":"moog-no-eq"}
ROM="4e143b94f758734f594ded78f4e5115635975c16fa37fabeae0baa4938ca710e"
SBK="fd2e35a260fef22fe809918dda3c921c6d48d53a29c3515af8a41019ce72d586"
TOL={"rms_abs_db":0.5,"peak_abs_db":1.0,"envelope_min":0.97,
     "spectrum_abs_db":1.0,"stereo_side_abs_db":1.0,"lr_balance_abs_db":1.0}
VOICE_REGS=("IFATN","PTRX_LO","PTRX_HI","CSL_HI","CSL_LO","PSST_HI",
           "PSST_LO","CCCA_LO","CCCA_HI","ATKHLDV","DCYSUSV","VTFT_HI","CVCF_HI")

def demand(c,msg):
    if not c: raise ValueError("P232_INVALID_COMPARISON: "+str(msg))

def checksum(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def db(v):
    return 20*math.log10(max(v,1e-10))

def last_registers(data):
    out={}
    for voice,reg,val in data:
        if reg in VOICE_REGS:
            out[f"{voice}:{reg}"]=val
    return out

def stereo(pcm):
    left,right=pcm[:,0],pcm[:,1]
    l,r=float(np.sqrt(np.mean(left*left))),float(np.sqrt(np.mean(right*right)))
    mid=(left+right)*.5
    side=(left-right)*.5
    m=float(np.sqrt(np.mean(mid*mid)))
    s=float(np.sqrt(np.mean(side*side)))
    norm=float(np.linalg.norm(left)*np.linalg.norm(right))
    return {"lr_balance_db":round(db(l)-db(r),4),
            "side_over_mid_db":round(db(s)-db(m),4),
            "interchannel_corr":round(float(np.dot(left,right)/norm) if norm>1e-12 else 0,5),
            "left_rms_dbfs":round(db(l),4),
            "right_rms_dbfs":round(db(r),4)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--original",type=Path,required=True)
    ap.add_argument("--p48",type=Path,required=True)
    ap.add_argument("--p67",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--product-sha",required=True)
    ap.add_argument("--original-86box-sha",required=True)
    ap.add_argument("--driver-staging",type=Path,required=True)
    args=ap.parse_args()
    demand(not args.out.exists(),"refuse overwrite")
    guest=json.loads(args.p48.read_text())
    bridge=json.loads(args.p67.read_text())
    demand(guest.get("hardware")=="sbawe64_gold","not AWE64 Gold")
    demand(bridge.get("agent_launched_in_actual_win95") is True,"original Win95 agent not proven")
    demand(bridge.get("original_creative_winmm_endpoint_selected") is True,
           "original Creative WinMM endpoint not proven")
    demand(bridge.get("audio_observed") is True,"no original audio tap proof")
    manifest=guest.get("p230_original_gm_8_capture",{})
    notes=manifest.get("cases",[])
    demand(len(notes)>=8,"incomplete original GM + drum capture")
    by_name={x["file"]:x for x in notes}
    demand(len(by_name)==len(notes),"duplicate original note identifiers")
    stage=json.loads(args.driver_staging.read_text())
    original_hashes={"rom":ROM,"sbk":SBK}
    for k,p in [("rom",args.root/"media/awe32.raw"),
                ("sbk",args.root/"media/SYNTHGM.SBK")]:
        demand(checksum(p)==original_hashes[k],"actual private ROM/SBK SHA differs")

    records=[]
    invalid=[]
    for case in notes:
        if not case["valid_original_pcm"]:
            invalid.append({"name":case["file"],"why":"original Creative wavetable near-silence",
                "original_audio":case["pcm_observed"],
                "original_ATKHLDV":[f"0x{v:04X}" for _,r,v in case["register_write_sequence"] if r=="ATKHLDV"]})
    for program in P:
        name=f"gm_b16383_p{program:03}_n060_v100.wav"
        demand(name in by_name,"missing program "+name)
        orig=by_name[name]
        demand(orig.get("valid_original_pcm") is True,"original reference inaudible "+name)
        demand((orig["bank"],orig["note"],orig["velocity"],orig["channel"])==(16383,60,100,0),
               "original MIDI mismatch "+name)
        orig_file=args.original/name
        demand(orig_file.exists() and checksum(orig_file)==orig["reference_sha256"],
               "original WAV checksum not equal guest verified capture")
        original_pcm=read_wav(orig_file).astype(np.float64)/32768
        result={}
        base_registers=None
        for variant,dirname in VAR.items():
            candidate=args.root/dirname/name
            native_pcm=read_wav(candidate).astype(np.float64)/32768
            native_trace_file=args.root/dirname/"traces"/(name+".trace")
            registers=native_trace(native_trace_file)
            if base_registers is None:base_registers=registers
            demand(base_registers==registers,"A/B/C/D register mismatch "+name)
            final_original=last_registers(orig["register_write_sequence"])
            final_native=last_registers(registers)
            mismatch={k:{"creative":v,"native":final_native.get(k)}
                      for k,v in final_original.items() if v!=final_native.get(k)}
            # Once the original driver has written its preset+effects registers,
            # all four variants must have the same effective voice register state.
            # Never erase real audio findings merely because register parity fails.
            # The case is flagged NOT equal-state instead of silently passing.
            pcm=compare_pair(orig_file,candidate)
            offset,_=lag(read_wav(orig_file),read_wav(candidate))
            o,n=align(read_wav(orig_file),read_wav(candidate),offset)
            st_o,st_n=stereo(o),stereo(n)
            side_delta=round(st_o["side_over_mid_db"]-st_n["side_over_mid_db"],3)
            balance_delta=round(st_o["lr_balance_db"]-st_n["lr_balance_db"],3)
            pcm["original_stereo"]=st_o
            pcm["native_stereo"]=st_n
            pcm["stereo_side_difference_db"]=side_delta
            pcm["lr_balance_difference_db"]=balance_delta
            pcm["audio_sha256"]={"original":checksum(orig_file),"125a":checksum(candidate)}
            pcm["effect_register_final_match"]=not bool(mismatch)
            pcm["effect_register_final_mismatches"]=mismatch
            # Pre-registered tolerance classification, but not automatically
            # a valid equal-state result until independent DSP init and capture
            # timing have been verified.
            pcm["within_numeric_tolerances"]=(abs(pcm["reference_minus_native_rms_db"])<=TOL["rms_abs_db"]
                and abs(pcm["reference_peak_dbfs"]-pcm["native_peak_dbfs"])<=TOL["peak_abs_db"]
                and pcm["envelope_correlation"]>=TOL["envelope_min"]
                and all(abs(x)<=TOL["spectrum_abs_db"] for x in pcm["reference_minus_native_bands_db"].values())
                and abs(side_delta)<=TOL["stereo_side_abs_db"]
                and abs(balance_delta)<=TOL["lr_balance_abs_db"])
            pcm["diagnostic_score"]=(abs(pcm["reference_minus_native_rms_db"])/TOL["rms_abs_db"]
                +abs(pcm["reference_peak_dbfs"]-pcm["native_peak_dbfs"])/TOL["peak_abs_db"]
                +(1-pcm["envelope_correlation"])/max(1-TOL["envelope_min"],1e-4)
                +sum(abs(x) for x in pcm["reference_minus_native_bands_db"].values())/5
                +abs(side_delta)/TOL["stereo_side_abs_db"]+abs(balance_delta)/TOL["lr_balance_abs_db"])
            result[variant]=pcm
        ranked=sorted(result,key=lambda k:result[k]["diagnostic_score"])
        records.append({"program":program,"original_name":name,"variants":result,
                        "diagnostic_best":ranked[0],
                        "diagnostic_rank_order":ranked,
                        "registers_identical_all_four_and_equal_to_original":all(
                            m["effect_register_final_match"] for m in result.values())})
    report={"schema":"125A-P232-original-Win95-4way-recapture-v1",
        "source_product_commit":args.product_sha,"source_86box_commit":args.original_86box_sha,
        "driver_staging_sha256":checksum(args.driver_staging),
        "original_p48_sha256":checksum(args.p48),
        "original_p67_sha256":checksum(args.p67),
        "original_sha256":original_hashes,
        "tolerance_version":"P232-predeclared-v1",
        "tolerances":TOL,
        "original_win95_86box_verified":True,
        "original_driver_staging":stage,
        "original_vs_native_matching_note_registers":all(
            c["registers_identical_all_four_and_equal_to_original"] for c in records),
        "original_chip_initialization_full_state_verified":False,
        "original_capture_note_on_timing_sample_aligned_verified":False,
        "original_and_native_effect_internal_returns_identical_verified":False,
        "equal_state_status":"NOT_CERTIFIED: initial chip state, FX return and sample-accurate timing not independently proven",
        "actual_original_Win95_pcm_vs_A_D_numeric_diagnostics":len(records)*4,
        "verified_equal_state_pairs":0,"verified_tolerance_passes":0,
        "verified_fixes":0,"verified_regressions":0,
        "gm":records,"drum_original_invalid":invalid,
        "release":"BLOCKED"}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n")
    for c in records:
        print(f'GM={c["program"]} diagnostic ranking={",".join(c["diagnostic_rank_order"])}')
        for k in VAR:
            m=c["variants"][k]
            print(f"  {k} RMS={m['reference_minus_native_rms_db']:+.3f}dB"
                  f" Envelope={m['envelope_correlation']:.4f}"
                  f" Spectral_max={max(abs(v) for v in m['reference_minus_native_bands_db'].values()):.2f}dB"
                  f" SideDiff={m['stereo_side_difference_db']:+.2f}dB"
                  f" BalanceDiff={m['lr_balance_difference_db']:+.2f}dB"
                  f" clip_original/native={m['reference_rail_samples']}/{m['native_rail_samples']}")
    print("P232_REAL_ORIGINAL_RECAPTURE_DIAGNOSTIC",len(records)*4,
          "NOT_CERTIFIED_EQUAL_STATE=TRUE drum_invalid=",len(invalid),
          "ENGINE_UNMODIFIED release=BLOCKED")
if __name__=="__main__":main()
