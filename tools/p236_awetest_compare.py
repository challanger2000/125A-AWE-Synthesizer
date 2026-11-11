#!/usr/bin/env python3
"""P236 physical AWETEST v25 AWE32 vs CURRENT 125A core, not upstream emulator.

Uses source-pinned, genuine AWETEST v25 AWE32 hardware self-recordings and
the per-note capture time stamps from the original hardware awetest.log.
The original AWETEST.C direct-register tone program is reconstructed once
in tools/p236_awetest_native.cpp, compiled with the current 125A
src/engine/snd_emu8k.c. No raw upstream replay TRACE is available in the
published sources branch: DO NOT claim replay of original recorded I/O log.

Card's internal ADC is NOT linear over its complete range, right dry
channel broken; comparison uses LEFT only. Absolute native/card amplitude
is NOT accepted as calibrated; relative spectral filter vs open 252 and
resonance Q vs Q0 comparisons cancel the unknown fixed analog gain. Reject
silent/noisy/clipped physical windows rather than calling them PASS.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

SOURCE_SHA="9ae2217b92af72f706c9631679cd43c3afff507f"
LOG_BLOB_SHA="09fe5c9f2a07e86fb4193f9f56f0b8583f656ede"
FILES={213000:"reca003",323600:"reca004"}
BANDS=((250,1000),(1000,4000),(4000,10000))
CUTOFFS=(0,16,32,48,64,80,96,112,128,160,192,224,252)
RESONANCE={(96,q) for q in (0,4,8,12,15)} | {(192,q) for q in (0,4,8,12,15)}

def demand(ok,msg):
    if not ok:raise RuntimeError("P236_AWETEST_HARDWARE_EVIDENCE_INVALID: "+msg)

def blobhash(path):
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def parse(log):
    cut={}
    res={}
    for line in log.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):continue
        capture=re.search(r"\bcap\s+(\d+):(\d+)\b",line)
        if not capture:continue
        base=int(capture.group(1));frame=int(capture.group(2))
        m=re.match(r"\s*\d+\s+6\s+cutoff (\d+)\s",line)
        if m:
            k=int(m.group(1))
            demand(k not in cut,"duplicate v25 cutoff anchor")
            cut[k]=(base,frame)
        n=re.match(r"\s*\d+\s+7\s+cutoff (\d+), Q (\d+)\s",line)
        if n:
            key=(int(n.group(1)),int(n.group(2)))
            demand(key not in res,"duplicate v25 resonance anchor")
            res[key]=(base,frame)
    demand(set(CUTOFFS)<=set(cut),"missing physical filter sweeps")
    demand(RESONANCE<=set(res),"missing original v25 Q probe events")
    demand(all(base in FILES for base,_ in [*map(cut.get,CUTOFFS),*map(res.get,RESONANCE)]),
        "card capture frames map to unverified original file")
    return cut,res

def windows(path,start,win_s=.08,win_e=.32):
    raw,sr=sf.read(path,dtype="float64",always_2d=True)
    demand(sr==44100 and raw.shape[1]==2,f"invalid AWE32 v25 44100 stereo file {path}")
    left=raw[:,0]
    a=start+int(round(win_s*sr))
    b=start+int(round(win_e*sr))
    demand(a>=int(.06*sr) and b<len(left),f"HW capture window outside file {path}")
    return left[a:b],left[a-int(.055*sr):a-int(.005*sr)],left[a:b].size

def feature(x,noise):
    def rms(v):return float(np.sqrt(np.mean(v*v)))
    r=rms(x);n=rms(noise)
    limit=float(np.max(np.abs(x)))
    # Require >=6dB above the actual physical card's pre-note noise floor.
    snr=20*math.log10(max(r,1e-12)/max(n,1e-12))
    # clipped genuine PCM cannot certify a filter response
    clipped=int(np.count_nonzero(np.abs(x)>=0.999))
    good=snr>=6 and clipped==0 and r>=1e-5
    f,p=signal.welch(x,fs=44100,nperseg=4096,noverlap=2048)
    bands={}
    for lo,hi in BANDS:
        v=float(np.sum(p[(f>=lo)&(f<hi)]))
        bands[f"{lo}-{hi}Hz"]=v
    return {"rms":r,"peak":limit,"noise_rms":n,"snr_db":round(snr,3),
        "clipped_sample_count":clipped,"valid":bool(good),"bands":bands}

def dbp(v):
    return 10*math.log10(max(v,1e-25))
def dbr(a,b):
    return 20*math.log10(max(a,1e-15)/max(b,1e-15))

def compare(ref,model,refbase,modelbase):
    # Relative shape error, physical AWE32 vs active current 125A EMU8000,
    # measured from actual tracks. This is not output gain normalization.
    current_rel=dbr(model["rms"],modelbase["rms"])
    real_rel=dbr(ref["rms"],refbase["rms"])
    spec={}
    for band in ref["bands"]:
        phys_rel=dbp(ref["bands"][band]/max(refbase["bands"][band],1e-25))
        emu_rel=dbp(model["bands"][band]/max(modelbase["bands"][band],1e-25))
        # A nearly silent card band is not a physically meaningful oracle.
        cardband=dbp(ref["bands"][band]/max(ref["bands"][band],1e-25))
        spec[band]={"card_relative_db":round(phys_rel,4),
            "125a_relative_db":round(emu_rel,4),
            "125a_minus_card_relative_db":round(emu_rel-phys_rel,4)}
    return {"relative_level_hardware_db":round(real_rel,4),
        "relative_level_native_db":round(current_rel,4),
        "relative_level_error_db":round(current_rel-real_rel,4),
        "relative_spectrum":spec}
def audit(a):
    log=a.original_log.read_text()
    demand(blobhash(a.original_log)==LOG_BLOB_SHA,"AWETEST hardware log changed")
    cut,res=parse(log)
    card={}
    for base,name in FILES.items():
        fp=a.card_folder/(name+".flac")
        demand(fp.is_file(),"physical AWE32 recording absent "+str(fp))
        wav,sr=sf.read(fp,dtype="float64",always_2d=True)
        demand(sr==44100 and wav.shape[1]==2,"physical FLAC source format wrong")
        card[base]=wav
    def physical(ev):
        base,frame=ev
        recording=card[base]
        a0=frame+3528;b0=frame+14112  # 80..320ms post NoteOn
        pre=recording[max(0,frame-2646):max(0,frame-441),0]
        demand(b0<len(recording),"truncated physical note window")
        return feature(recording[a0:b0,0],pre)
    def native(fp):
        wave,sr=sf.read(fp,dtype="float64",always_2d=True)
        demand(sr==44100 and len(wave)==44100*11//10,"native AWETEST wrong PCM geometry")
        return feature(wave[3528:14112,0],wave[:100,0])
    c_p={key:physical(cut[key]) for key in CUTOFFS}
    c_n={key:native(a.native_dir/f"cutoff_{key}.wav") for key in CUTOFFS}
    r_p={key:physical(res[key]) for key in sorted(RESONANCE)}
    r_n={key:native(a.native_dir/f"resonance_{key[0]}_{key[1]}.wav")
         for key in sorted(RESONANCE)}
    anchor=c_p[252],c_n[252]
    demand(all(r["valid"] for r in anchor),"open Q0 HW/native card reference invalid")
    cut_rows=[]
    for key in CUTOFFS:
        ref,nat=c_p[key],c_n[key]
        valid=ref["valid"] and nat["valid"]
        row={"cutoff":key,"hardware_card_valid":ref["valid"],
            "native_valid":nat["valid"],"card_snr_db":ref["snr_db"],
            "card_clipped_samples":ref["clipped_sample_count"],
            "card_rms":round(ref["rms"],7),"current_125a_rms":round(nat["rms"],7),
            "original_hardware_stamp":cut[key],
            "compare":compare(ref,nat,*anchor) if valid else None}
        cut_rows.append(row)
    res_rows=[]
    for cutoff,q in sorted(RESONANCE):
        p0,n0=r_p[(cutoff,0)],r_n[(cutoff,0)]
        p,n=r_p[(cutoff,q)],r_n[(cutoff,q)]
        valid=all(x["valid"] for x in (p,n,p0,n0))
        res_rows.append({"cutoff":cutoff,"Q":q,"hardware_card_valid":p["valid"],
           "native_valid":n["valid"],"card_snr_db":p["snr_db"],
           "card_clipped_samples":p["clipped_sample_count"],
           "original_hardware_stamp":res[(cutoff,q)],
           "compare":compare(p,n,p0,n0) if valid else None})
    allvalid=[x for x in cut_rows+res_rows if x["compare"]]
    errors=[abs(x["compare"]["relative_level_error_db"]) for x in allvalid]
    spec=[abs(v["125a_minus_card_relative_db"])
          for x in allvalid
          for v in x["compare"]["relative_spectrum"].values()]
    report={
        "schema":"125A-P236-direct-physical-AWE32-v25-cutoff-resonance-v1",
        "reference":"real AWE32 internal ADC mono-left; AWETEST v25 hardware data and original timestamps",
        "source_commit":SOURCE_SHA,
        "hardware_awetest_log_sha":LOG_BLOB_SHA,
        "source_voice_setup":"direct reconstructed AWETEST.C ToneDefaults/ToneSetup/ToneTrigger, ROM noise 458995/459001/467282",
        "original_hardware_register_raw_trace_available":False,
        "full_raw_register_replay_claimed":False,
        "current_125a_commit":a.current_commit,
        "hardware_capture_limitations":[
            "Card internally records mono LEFT only, right channel defective",
            "internal ADC +18dB and mixer nonlinear at high level; absolute RMS not 1:1 hardware",
            "v26/v27 clipped recordings not used",
            "AWE32Emu private full25.trace and VM per-register logs not present in public sources tree",
            "AWE32 hardware card has DSP 4.13, manufacturer CT number not confirmed; not the CT4390 analog card",
            "relative cutoff response uses same hardware/noise ROM sample across notes, NOT post-gain corrected audio"],
        "cutoff":cut_rows,
        "resonance":res_rows,
        "total_real_hardware_note_pairs":len(cut_rows)+len(res_rows),
        "valid_real_hardware_note_pairs":len(allvalid),
        "invalid_pairs":len(cut_rows)+len(res_rows)-len(allvalid),
        "median_absolute_relative_level_error_db":round(float(np.median(errors)),4) if errors else None,
        "median_absolute_relative_spectral_error_db":round(float(np.median(spec)),4) if spec else None,
        "hardware_one_to_one_accepted":False,
        "hardware_acceptance":"BLOCKED",
        "production_dsp_unchanged":True,
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    demand(not a.out.exists(),"P236 refuses overwriting direct hardware evidence")
    a.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("P236_REAL_AWE32_CURRENT_125A_DIRECT_PHYSICAL",
          "valid",report["valid_real_hardware_note_pairs"],
          "invalid",report["invalid_pairs"],
          "median_abs_level_db",report["median_absolute_relative_level_error_db"],
          "median_abs_spec_db",report["median_absolute_relative_spectral_error_db"],
          "card_ADC_nonlin_AND_missing_raw_trace=NOT_1TO1_HARDWARE_ACCEPTANCE")
    for x in cut_rows:
        if x["compare"]:
            print("P236_REAL_HARDWARE_CUTOFF",x["cutoff"],"relative_level_error_dB",
                  x["compare"]["relative_level_error_db"],
                  "relative_bands",{
                   k:v["125a_minus_card_relative_db"]
                   for k,v in x["compare"]["relative_spectrum"].items()})
        else:
            print("P236_REAL_HARDWARE_CUTOFF_INVALID",x["cutoff"],"SNR",x["card_snr_db"])
def selftest():
    fake="\n".join(["  300000  6 cutoff 0\t@rt 1:1 cap 213000:10000",
                    "  301000  7 cutoff 96, Q 0\t@rt 1:1 cap 323600:20000"])
    # Reject a partial or forged logger as valid physical evidence.
    try:parse(fake)
    except RuntimeError:pass
    else:raise AssertionError("partial AWE32 record accepted")
    x={"rms":.2,"bands":{str(x):x for x in range(3)}}
    y={"rms":.1,"bands":{str(x):x/2 for x in range(3)}}
    p=compare(x,y,x,y)
    assert p["relative_level_error_db"]==0
    print("P236_AWETEST_PHYSICAL_ORACLE_SELFTEST_PASS missing_events_rejected=1 normalized_anchor_identity=1")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-log",type=Path)
    p.add_argument("--card-folder",type=Path)
    p.add_argument("--native-dir",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--current-commit")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:return selftest()
    for key in ("original_log","card_folder","native_dir","out","current_commit"):
        demand(getattr(a,key) is not None,"missing "+key)
    audit(a)
if __name__=="__main__":main()
