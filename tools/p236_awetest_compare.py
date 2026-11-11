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
BANDS=((0,50),(50,250),(250,1000),(1000,4000),(4000,10000),(10000,22050))
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
    ac=rms(x-np.mean(x))
    # Quantify the 0..250 Hz and DC energy that the original three spectral
    # bands omitted. Diagnose only: do not filter either audio signal in DSP.
    sos=signal.butter(4,250,btype="highpass",fs=44100,output="sos")
    highpass250=rms(signal.sosfiltfilt(sos,x))
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
    spectral_sum=sum(bands.values())
    fractions={band:round(power/max(spectral_sum,1e-25),6)
               for band,power in bands.items()}
    return {"rms":r,"ac_rms":ac,"above_250hz_rms":highpass250,
        "dc_mean":float(np.mean(x)), "peak":limit,"noise_rms":n,"snr_db":round(snr,3),
        "clipped_sample_count":clipped,"valid":bool(good),"bands":bands,
        "spectral_energy_fractions":fractions}

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
    def relative_metric_error(k):
        return round(dbr(model[k],modelbase[k])-dbr(ref[k],refbase[k]),4)
    return {"relative_level_hardware_db":round(real_rel,4),
        "relative_level_native_db":round(current_rel,4),
        "relative_level_error_db":round(current_rel-real_rel,4),
        "relative_ac_level_error_db":relative_metric_error("ac_rms"),
        "relative_above_250hz_level_error_db":relative_metric_error("above_250hz_rms"),
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
            "card_dc_mean":round(ref["dc_mean"],9),"current_125a_dc_mean":round(nat["dc_mean"],9),
            "card_above_250hz_rms":round(ref["above_250hz_rms"],8),
            "current_125a_above_250hz_rms":round(nat["above_250hz_rms"],8),
            "card_spectral_energy_fractions":ref["spectral_energy_fractions"],
            "native_spectral_energy_fractions":nat["spectral_energy_fractions"],
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
    # These are diagnostics, not a replacement for the true broadband RMS.
    # A large total-RMS error with a small >250Hz error isolates a frequency-
    # dependent or DC/capture component before changing a verified filter.
    # Never hide a severe cutoff mismatch behind the good resonance cases.
    cut_errors=[abs(x["compare"]["relative_level_error_db"])
                for x in cut_rows if x["compare"]]
    # Q0 is the reference by definition: its exactly-zero error is tautological
    # and must not inflate the resonance fidelity score.
    res_errors=[abs(x["compare"]["relative_level_error_db"])
                for x in res_rows if x["Q"]>0 and x["compare"]]
    cut_ac_errors=[abs(x["compare"]["relative_ac_level_error_db"])
                   for x in cut_rows if x["compare"]]
    cut_above250_errors=[abs(x["compare"]["relative_above_250hz_level_error_db"])
                         for x in cut_rows if x["compare"]]
    # Optional stationary-noise sensitivity estimate, not an audio correction
    # and not a calibrated analog ADC inversion. Report both estimates.
    def hw_signal_only_rms(f):
        return math.sqrt(max(0.,f["rms"]**2-f["noise_rms"]**2))
    anchor_signal=hw_signal_only_rms(anchor[0])
    for row in cut_rows:
        if row["compare"]:
            ref=c_p[row["cutoff"]]
            signal=hw_signal_only_rms(ref)
            if signal>1e-12 and anchor_signal>1e-12:
                hw_rel_signal=dbr(signal,anchor_signal)
                emu_rel=row["compare"]["relative_level_native_db"]
                row["relative_level_error_db_stationary_noise_sensitivity"]=round(
                    emu_rel-hw_rel_signal,4)
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
        "median_absolute_cutoff_level_error_db":round(float(np.median(cut_errors)),4) if cut_errors else None,
        "median_absolute_cutoff_ac_level_error_db":round(float(np.median(cut_ac_errors)),4) if cut_ac_errors else None,
        "median_absolute_cutoff_above_250hz_level_error_db":round(float(np.median(cut_above250_errors)),4) if cut_above250_errors else None,
        "median_absolute_resonance_nonzero_Q_level_error_db":round(float(np.median(res_errors)),4) if res_errors else None,
        "resonance_Q0_reference_points_excluded_from_fidelity_score":2,
        "median_absolute_relative_spectral_error_db":round(float(np.median(spec)),4) if spec else None,
        "stationary_noise_sensitivity_not_adc_calibration":True,
        "dc_and_above_250hz_measurements_are_only_diagnostics":True,
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
          "cutoff_median_abs_level_db",report["median_absolute_cutoff_level_error_db"],
          "cutoff_ac_median_abs_level_db",report["median_absolute_cutoff_ac_level_error_db"],
          "cutoff_above250_median_abs_level_db",report["median_absolute_cutoff_above_250hz_level_error_db"],
          "resonance_Q_positive_median_abs_level_db",report["median_absolute_resonance_nonzero_Q_level_error_db"],
          "card_ADC_nonlin_AND_missing_raw_trace=NOT_1TO1_HARDWARE_ACCEPTANCE")
    for x in cut_rows:
        if x["compare"]:
            print("P236_REAL_HARDWARE_CUTOFF",x["cutoff"],"relative_level_error_dB",
                  x["compare"]["relative_level_error_db"],
                  "relative_ac_level_error_db",x["compare"]["relative_ac_level_error_db"],
                  "relative_above250_level_error_db",x["compare"]["relative_above_250hz_level_error_db"],
                  "card_dc",x["card_dc_mean"],"native_dc",x["current_125a_dc_mean"],
                  "reference_high10k_frac",x["card_spectral_energy_fractions"]["10000-22050Hz"],
                  "native_high10k_frac",x["native_spectral_energy_fractions"]["10000-22050Hz"],
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
    # All comparative metrics must have independent normalization identities.
    x.update({"ac_rms":.2,"above_250hz_rms":.1})
    y.update({"ac_rms":.1,"above_250hz_rms":.05})
    p=compare(x,y,x,y)
    assert p["relative_level_error_db"]==0
    assert p["relative_ac_level_error_db"]==0
    assert p["relative_above_250hz_level_error_db"]==0
    ff=feature(np.sin(2*np.pi*80*np.arange(11000)/44100),np.zeros(1000))
    assert ff["above_250hz_rms"]<.05*ff["rms"]
    assert ff["bands"]["50-250Hz"]>ff["bands"]["250-1000Hz"]
    print("P236_AWETEST_PHYSICAL_ORACLE_SELFTEST_PASS missing_events_rejected=1 normalized_anchor_identity=1")

def line_out_audit(a):
    """Compare the SAME v25 card's external LINE OUT, not its internal ADC.

    Clock fit is the two-reference-tone subset of the hardware author's
    analysis/flac25.py. Hard fail on bad alignment or a clipped/absent anchor.
    This is strictly offline evidence; no DSP or normalization is applied.
    """
    log=a.original_log.read_text()
    demand(blobhash(a.original_log)==LOG_BLOB_SHA,"line-out log provenance")
    events=[]
    for line in log.splitlines():
        m=re.match(r"\s*\d+\s+(\d+)\s+(.+?)\s+@rt\s+(\d+):(\d+)\s+cap\s+(\d+):(\d+)\s*$",line)
        if m:
            block=int(m.group(1))
            ev={"block":block,"text":m.group(2).strip(),
                "rt":(int(m.group(3))*65536+int(m.group(4)))/1193182.,
                "filebase":int(m.group(5)),"frame":int(m.group(6))}
            events.append(ev)
    # Match source analysis/flac25.py across the full recording, including
    # mid-run references. The first two source anchors were reproducible
    # (r=.935/.947), but v25 blocks 5 and 6 have low envelope correlation;
    # accepting only these four yields a false missing-clock conclusion.
    # Also preserve all THREE consecutive original external FLAC parts.
    card_by_base={
        0:"reca001.flac",101800:"reca002.flac",213000:"reca003.flac",
        323600:"reca004.flac",434800:"reca005.flac",
        548252:"reca006.flac",660287:"reca007.flac"}
    # Reuse the full original author's 1..11 reference-tone clock-fit.
    # Include repeated checkpoint tones as well: v25 block 4/5/6 first
    # checkpoints exhibit low cross-correlation, not an absent recording.
    anchors=[e for e in events if e["text"]=="reference tone"
             and 1<=e["block"]<=11 and e["filebase"] in card_by_base]
    demand(any(e["block"]==1 for e in anchors)
           and any(e["block"]>=7 for e in anchors),
           "missing full physical v25 clock references")
    pieces=[]
    for fp in a.line_parts:
        info=sf.info(fp)
        demand(info.samplerate==44100 and info.channels==2,"invalid external line format")
        pieces.append((fp,info.frames))
    length=sum(n for _,n in pieces)
    def read_line(t0,t1):
        n0=int(round(t0*44100))
        n1=int(round(t1*44100))
        demand(0<=n0<n1<=length,"external line recording does not cover event")
        out=[];off=0
        for fp,n in pieces:
            lo=max(n0-off,0);hi=min(n1-off,n)
            if hi>lo:
                with sf.SoundFile(fp) as src:
                    src.seek(lo)
                    out.append(src.read(hi-lo,dtype="float64",always_2d=True)[:,0])
            off+=n
        return np.concatenate(out)
    def env10(x):
        h=441;n=len(x)//h*h
        e=np.log(np.mean(x[:n].reshape(-1,h)**2,axis=1)+1e-10)
        return e-e.mean()
    # The author's first-anchor provenance is 21.76s from the start of
    # the unsplit line recording to the start of reca001.
    reference=anchors[0]
    predicted_base=21.76+reference["frame"]/44100.
    found=[]
    for anchor in anchors:
        pred=predicted_base+anchor["rt"]-reference["rt"]
        if pred<4 or pred+7>length/44100.:
            print("P236_EXTERNAL_LINE_ANCHOR_OUTSIDE_CAPTURE",
                  anchor["block"],round(pred,4),flush=True)
            continue
        demand(anchor["filebase"] in card_by_base,
               "unknown original capture segment for reference tone")
        fp=a.card_folder/card_by_base[anchor["filebase"]]
        card,sr=sf.read(fp,dtype="float64",always_2d=True)
        demand(sr==44100,"invalid anchor internal card")
        c0=int(anchor["frame"]-44100)
        c1=int(anchor["frame"]+4*44100)
        demand(c0>=0 and c1<=len(card),"internal anchor out of bounds")
        ce=env10(card[c0:c1,0])
        fe=env10(read_line(pred-4.,pred+7.))
        corr=np.correlate(fe,ce,"valid")
        idx=int(np.argmax(corr))
        quality=float(np.corrcoef(fe[idx:idx+len(ce)],ce)[0,1])
        got=pred-4+idx*.01+1.
        print("P236_EXTERNAL_LINE_ANCHOR",anchor["block"],
              "predicted_s",round(pred,4),"found_s",round(got,4),
              "correlation",round(quality,4),"offset_s",round(got-pred,4),
              flush=True)
        if quality>.60 and abs(got-pred)<3.0:
            found.append((anchor["block"],anchor["rt"],got,quality))
    demand(len(found)>=3 and any(e[0]>=4 for e in found)
           and any(e[0]<=2 for e in found),
           "physical line-out lacks independent near/mid/late trusted reference tones")
    slope,intercept=np.polyfit([p[1] for p in found],[p[2] for p in found],1)
    residual=np.asarray([p[2]-(slope*p[1]+intercept) for p in found])
    demand(.995<slope<1.005 and np.max(np.abs(residual))<.03,
           "external line clock drift or anchor residual outside tolerance")
    anchors_text=[{"block":int(block),"rt":round(rt,7),
                  "line_time_s":round(sec,4),
                  "envelope_correlation":round(q,4)}
                  for block,rt,sec,q in found]
    cut_ev={}
    for e in events:
        m=re.fullmatch(r"cutoff (\d+)",e["text"])
        if e["block"]==6 and m:
            cut_ev[int(m.group(1))]=e
    demand(set(CUTOFFS)<=set(cut_ev),"external line cutoff notes missing")
    card={}
    native={}
    internal={}
    original_internal,sr=sf.read(a.card_folder/"reca003.flac",
                                 dtype="float64",always_2d=True)
    demand(sr==44100 and original_internal.shape[1]==2,
           "AWE32 internal ADC recording wrong format")
    for cutoff in CUTOFFS:
        e=cut_ev[cutoff]
        demand(e["filebase"]==213000,
               "cutoff note not in original reca003")
        t=slope*e["rt"]+intercept
        card[cutoff]=feature(read_line(t+.08,t+.32),read_line(t-.06,t-.01))
        frame=e["frame"]
        demand(frame>2646 and frame+14112<len(original_internal),
               "internal ADC window outside actual recording")
        internal[cutoff]=feature(original_internal[frame+3528:frame+14112,0],
                                original_internal[frame-2646:frame-441,0])
        wav,sr=sf.read(a.native_dir/f"cutoff_{cutoff}.wav",
                       dtype="float64",always_2d=True)
        demand(sr==44100,"line-out native WAV rate")
        native[cutoff]=feature(wav[3528:14112,0],np.zeros(2000))
    demand(card[252]["valid"] and native[252]["valid"] and internal[252]["valid"],
           "external LINE / internal ADC / native wide-open anchor invalid")
    rows=[]
    for cutoff in CUTOFFS:
        x,y,z=card[cutoff],native[cutoff],internal[cutoff]
        trusted=x["valid"] and y["valid"] and z["valid"]
        path_bias=(dbr(z["rms"],internal[252]["rms"])-
                   dbr(x["rms"],card[252]["rms"])) if trusted else None
        rows.append({"cutoff":cutoff,"line_capture_valid":x["valid"],
                     "line_snr_db":x["snr_db"],"line_clipped_samples":x["clipped_sample_count"],
                     "simultaneous_internal_ADC_valid":z["valid"],
                     "simultaneous_internal_ADC_snr_db":z["snr_db"],
                     "internal_ADC_minus_line_relative_rms_db":
                         round(path_bias,4) if path_bias is not None else None,
                     "compare":compare(x,y,card[252],native[252])
                       if x["valid"] and y["valid"] else None})
    valid=[r for r in rows if r["compare"]]
    med=round(float(np.median([abs(r["compare"]["relative_level_error_db"])
                               for r in valid])),4) if valid else None
    capture_errors=[abs(r["internal_ADC_minus_line_relative_rms_db"])
                    for r in rows if r["cutoff"]!=252 and
                    r["internal_ADC_minus_line_relative_rms_db"] is not None]
    capture_median=round(float(np.median(capture_errors)),4) if capture_errors else None
    out={"schema":"P236-real-AWE32-v25-external-line-vs-125A",
         "source":"turican0 AWETST25 genuine simultaneous LINE OUT, author's flac25.py 2-anchor fit",
         "card_log_blob_sha":LOG_BLOB_SHA,"current_125a_commit":a.current_commit,
         "line_parts":[p.name for p in a.line_parts],
         "line_alignment":anchors_text,"line_clock_slope":round(float(slope),8),
         "valid_pairs":len(valid),"median_abs_cutoff_rms_error_db":med,
         "median_abs_original_internal_ADC_vs_line_cutoff_db":capture_median,
         "note_windows":rows,
         "conditions":"No EQ/gain correction or analog compensation; same actual native WAV and ROM",
         "release_audio_fidelity":"BLOCKED"}
    demand(not a.line_out.exists(),"external line-out evidence file already exists")
    a.line_out.write_text(json.dumps(out,indent=2)+"\n")
    print("P236_REAL_AWE32_EXTERNAL_LINE_CUTOFF",
          "valid",len(valid),"median_abs_level_error_db",med,
          "same_hardware_capture_path_median_abs_db",capture_median,
          "align",anchors_text)
    for item in rows:
        if item["compare"]:
            print("P236_REAL_LINE_CUTOFF",item["cutoff"],
                  "relative_level_error_db",item["compare"]["relative_level_error_db"],
                  "relative_bands",{k:v["125a_minus_card_relative_db"]
                                    for k,v in item["compare"]["relative_spectrum"].items()})
        else:
            print("P236_REAL_LINE_CUTOFF_INVALID",item["cutoff"],
                  "SNR",item["line_snr_db"],"clipped",item["line_clipped_samples"])

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-log",type=Path)
    p.add_argument("--card-folder",type=Path)
    p.add_argument("--native-dir",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--current-commit")
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--line-parts",type=Path,nargs=3)
    p.add_argument("--line-out",type=Path)
    a=p.parse_args()
    if a.self_test:return selftest()
    for key in ("original_log","card_folder","native_dir","out","current_commit"):
        demand(getattr(a,key) is not None,"missing "+key)
    audit(a)
    if a.line_parts or a.line_out:
        demand(a.line_parts is not None and a.line_out is not None,
               "line-out pieces and output must both be present")
        line_out_audit(a)
if __name__=="__main__":main()
