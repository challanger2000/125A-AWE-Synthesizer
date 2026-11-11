#!/usr/bin/env python3
"""P234: original Win95 Creative vs 125A exact pre-FX dry PCM note-edge audit.

All raw private PCM remains on runner. Only numeric JSON in artifact.
Never replace a real NoteOff register edge with assumed 'step 1000' or
'frame 44100'. No loudness-normalization, no preset-level corrections.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np

RATE=44100
SPECTRAL=((80,250),(250,1000),(1000,4000),(4000,10000),(10000,20000))
PROGRAMS=(0,39,88)
SLICES={
    "onset":lambda on,off:(on,on+22050),
    "before_noteoff":lambda on,off:(off-22050,off-2205),
    "at_noteoff":lambda on,off:(off-2205,off+2205),
    "after_noteoff":lambda on,off:(off+2205,off+22050),
}

def need(cond,msg):
    if not cond:raise ValueError("P234_UNVERIFIED: "+msg)

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def decode_rows(p,span=None):
    raw=p.read_bytes()
    if span:
        need(len(span)==2 and 0<=span[0]<span[1]<=len(raw),
             "invalid P233/P234 byte segment")
        raw=raw[span[0]:span[1]]
    P=[];Q=[];M=[]
    for line in raw.decode("utf8").splitlines():
        v=line.strip().split(",")
        if v[0]=="P":
            need(len(v)==4,"malformed raw PCM block")
            P.append(dict(frame=int(v[1]),n=int(v[2]),byte=int(v[3])))
        elif v[0]=="Q":
            need(len(v)==5,"malformed chip register edge")
            Q.append(dict(frame=int(v[1]),voice=int(v[2]),reg=int(v[3]),value=int(v[4],16)))
        elif v[0]=="M" and len(v)==10:
            M.append(dict(frame=int(v[1]),n=int(v[2]),stage=v[3],mid2=float(v[6]),side2=float(v[7])))
    return P,Q,M

def edges(Q):
    # DCYSUSV low 0x80 disables voice; high 0x8000 requests release.
    on=sorted(x["frame"] for x in Q if x["reg"]==5 and not(x["value"]&0x80)
              and not(x["value"]&0x8000))
    need(on,"no observed original/native DCYSUSV note-on register edge")
    first=on[0]
    off=sorted(x["frame"] for x in Q if x["reg"]==5 and x["value"]&0x8000
               and x["frame"]>first)
    need(off,"no observed original/native DCYSUSV note-off register edge")
    release=off[0]
    need(22050<=release-first<=88200,"implausible note-on to note-off duration")
    return {"noteon_chip_frame":first,"noteoff_chip_frame":release,
            "duration_frames":release-first,
            "noteon_layer_voices":sorted(set(x["voice"] for x in Q if x["reg"]==5
                 and not(x["value"]&0x80) and not(x["value"]&0x8000)
                 and first<=x["frame"]<=first+4410)),
            "noteoff_layer_voices":sorted(set(x["voice"] for x in Q if x["reg"]==5
                 and x["value"]&0x8000 and release<=x["frame"]<=release+4410)),
            "register_edges":Q}

def private_pcm(p,lo,hi):
    need(p.is_file() and p.stat().st_size%8==0,"private dry stereo int32le PCM absent")
    n=p.stat().st_size//8
    return np.memmap(p,mode="r",dtype="<i4",shape=(n,2))

def crop(rows,pcm,start,end,allowed=None):
    need(start<end,"empty sample-accurate window")
    raw=[]
    cursor=start
    for block in sorted(rows,key=lambda x:x["frame"]):
        bstart,bend=block["frame"],block["frame"]+block["n"]
        if bend<=cursor:continue
        if bstart>cursor:
            if bstart>=end:break
            raise ValueError(f"P234_UNVERIFIED: lost {bstart-cursor} sample frames before {bstart}")
        a,b=max(bstart,cursor),min(bend,end)
        if a>=b:continue
        ptr=block["byte"]//8+(a-bstart)
        need(block["byte"]%8==0 and ptr+(b-a)<=len(pcm),"bad raw PCM offset")
        if allowed:
            need(ptr*8>=allowed[0] and (ptr+b-a)*8<=allowed[1],
                 "dry PCM block escapes guest per-case private evidence window")
        raw.append(np.array(pcm[ptr:ptr+(b-a)],dtype=np.int32))
        cursor=b
        if cursor==end:break
    need(cursor==end,"incomplete true event-synchronized dry PCM coverage")
    out=np.concatenate(raw)
    need(len(out)==end-start,"sample-accurate window shape mismatch")
    return out

def db_power(v):
    return round(10*math.log10(max(float(v),1e-24)),3)

def db_amp(v):
    return round(20*math.log10(max(float(v),1e-12)),3)

def stats(chunk):
    x=chunk.astype(np.float64)/32768.0
    left=x[:,0];right=x[:,1]
    mid=(left+right)*.5;side=(left-right)*.5
    rmsL=math.sqrt(float(np.mean(left*left)))
    rmsR=math.sqrt(float(np.mean(right*right)))
    rmsMid=math.sqrt(float(np.mean(mid*mid)))
    rmsSide=math.sqrt(float(np.mean(side*side)))
    rho=float(np.dot(left,right)/(np.linalg.norm(left)*np.linalg.norm(right))) \
        if np.any(left) and np.any(right) else None
    nfft=4096
    mono=mid
    spectral={}
    if len(mono)>=nfft:
        nw=min(12,1+(len(mono)-nfft)//2048)
        windows=np.stack([mono[i*2048:i*2048+nfft] for i in range(nw)])
        p=np.mean(np.abs(np.fft.rfft(windows*np.hanning(nfft),axis=1))**2,axis=0)
        bins=np.fft.rfftfreq(nfft,1/RATE)
        spectral={f"{lo}-{hi}Hz":float(np.sum(p[(bins>=lo)&(bins<hi)]))
                  for lo,hi in SPECTRAL}
    hop=441
    n=len(mid)//hop
    envelope=np.sqrt(np.mean(mid[:n*hop].reshape(n,hop)**2,axis=1)) if n else np.array([])
    return dict(frames=len(chunk),left_rms_dbfs=db_amp(rmsL),
        right_rms_dbfs=db_amp(rmsR),mid_rms_dbfs=db_amp(rmsMid),
        side_rms_dbfs=db_amp(rmsSide),
        side_over_mid_db=db_amp(rmsSide/max(rmsMid,1e-12)),
        peak_dbfs=db_amp(np.max(np.abs(x))),
        lr_correlation=round(rho,6) if rho is not None else None,
        pre_int16_outside_rail_samples=int(np.count_nonzero((chunk>=32767)|(chunk<=-32768))),
        spectral_power=spectral,
        envelope_10ms=envelope.tolist())

def compare(a,b):
    ra=stats(a);rb=stats(b)
    need(ra["frames"]==rb["frames"],"unequal sample lengths")
    ea=np.array(ra.pop("envelope_10ms"))
    eb=np.array(rb.pop("envelope_10ms"))
    corr=float(np.corrcoef(ea,eb)[0,1]) if len(ea)>3 \
        and np.std(ea)>1e-9 and np.std(eb)>1e-9 else None
    bands={key:round(10*math.log10(max(ra["spectral_power"][key],1e-25)/
                      max(rb["spectral_power"][key],1e-25)),3)
           for key in ra["spectral_power"]}
    return dict(creative=ra,native=rb,
        creative_minus_native_left_rms_db=round(ra["left_rms_dbfs"]-rb["left_rms_dbfs"],3),
        creative_minus_native_right_rms_db=round(ra["right_rms_dbfs"]-rb["right_rms_dbfs"],3),
        original_minus_native_spectral_bands_db=bands,
        envelope_correlation=round(corr,5) if corr is not None else None,
        no_gain_matching=True)

def audit(args):
    guest=json.loads(args.p48.read_text())
    p67=json.loads(args.p67.read_text())
    need(guest.get("hardware")=="sbawe64_gold","not original Win95 Creative AWE64")
    need(p67.get("agent_launched_in_actual_win95") and
         p67.get("original_creative_winmm_endpoint_selected") and p67.get("audio_observed"),
         "original Win95 WinMM / P67 delivery provenance absent")
    cases={r["program"]:r for r in guest["p230_original_gm_8_capture"]["cases"]
           if r["bank"]==16383}
    need(all(p in cases for p in PROGRAMS),"GM0/39/88 guest original data missing")
    original_pcm=private_pcm(args.original_dry,None,None)
    output=[]
    for p in PROGRAMS:
        c=cases[p]
        need(c["valid_original_pcm"],f"GM{p} original WAV invalid")
        rows_o,qs_o,m_o=decode_rows(args.original_stage,c["p233_stage_file_byte_range"])
        original_meta=c.get("p234_dry_pcm_byte_range")
        need(original_meta and original_meta[0] is not None,f"GM{p} missing original raw per-note gate")
        rows_n,qs_n,m_n=decode_rows(args.native_root/f"native-gm{p}-stage.csv")
        raw_native=args.native_root/f"native-gm{p}-dry.i32le"
        pcm_native=private_pcm(raw_native,None,None)
        eo,en=edges(qs_o),edges(qs_n)
        verified_same_hold_duration=abs(eo["duration_frames"]-en["duration_frames"])<=44
        windows={}
        for key,f in SLICES.items():
            ao,bo=f(eo["noteon_chip_frame"],eo["noteoff_chip_frame"])
            an,bn=f(en["noteon_chip_frame"],en["noteoff_chip_frame"])
            need(bo-ao==bn-an,"window lengths unequal")
            x=crop(rows_o,original_pcm,ao,bo,original_meta)
            y=crop(rows_n,pcm_native,an,bn)
            windows[key]={"original_absolute_chip_frames":[ao,bo],
                          "native_absolute_chip_frames":[an,bn],
                          "metrics":compare(x,y)}
        wet_native={}
        for stage in ("reverb","chorus"):
            stage_rows=[row for row in m_n if row["stage"]==stage]
            wet_native[stage]={
                "sum_component_mid2":sum(r["mid2"] for r in stage_rows),
                "sum_component_side2":sum(r["side2"] for r in stage_rows)}
        no_native_fx=all(v["sum_component_mid2"]==0
                       and v["sum_component_side2"]==0 for v in wet_native.values())
        need(no_native_fx,f"GM{p} native GUI=0/dry wet-return leakage")
        # Original read-only raw tap is pre-FX, even if guest still
        # computes FX for its separately captured *wet* final output.
        output.append(dict(program=p,bank=16383,note=c["note"],velocity=c["velocity"],
            original_wav_sha256=c["reference_sha256"],
            native_raw_dry_sha256=digest(raw_native),
            original_dry_pcm_byte_range=original_meta,
            chip_register_edges={"original":eo,"native":en},
            note_duration_difference_frames=eo["duration_frames"]-en["duration_frames"],
            nominal_1000ms_not_substituted_for_actual_noteoff=True,
            same_note_hold_duration_within_1ms=verified_same_hold_duration,
            native_wet_return_component_energy=wet_native,
            native_both_fx_returns_verified_zero=no_native_fx,
            creative_reference_tap_is_pre_effects=True,
            reference_guest_original_fx_returns_were_not_modified=True,
            windows=windows,
            classification="NUMERIC_DIAGNOSIS_NOT_EQUAL_STATE_PASS"))
    drums=[r for r in guest["p230_original_gm_8_capture"]["cases"] if r["bank"]==16382]
    need(len(drums)==3,"three original drum invalid/valid cases absent")
    result=dict(schema="125A-P234-original-native-true-note-edge-dry-v1",
        reference="Original Win95 Creative WinMM on 86Box AWE64 Gold (not physical CT4390)",
        original_86box_sha=args.original_86box_sha,
        native_125a_sha=args.native_sha,
        observer_sha=args.observer_sha,
        original_P48_sha256=digest(args.p48),original_P67_sha256=digest(args.p67),
        original_dry_pcm_sha256=digest(args.original_dry),
        original_stage_sha256=digest(args.original_stage),
        actual_DSP_frame_noteon_noteoff_required=True,
        exact_44100Hz_time_window_cropping=True,
        no_volume_normalization=True,
        note="Unmodified original Creative guest; pre-FX dry observer excludes wet returns without driver muting. Native test-only GUI=0 with both FX returns explicitly muted. No VST3 host capture or full end-to-end sample-aligned output equal-state proof.",
        gm=output,
        invalid_original_drums=[dict(note=x["note"],valid=x["valid_original_pcm"])
                                for x in drums if not x["valid_original_pcm"]],
        verified_equal_state_pairs=0,
        full_77_preset_sf2_test="NOT_RUN",
        windows_VST3_host="NOT_RUN",
        release="BLOCKED")
    need(not args.out.exists(),"refuse overwrite P234 report")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    for r in output:
        print("P234_DRY_PROGRAM",r["program"],
              "noteon_off_original",r["chip_register_edges"]["original"]["noteon_chip_frame"],
              r["chip_register_edges"]["original"]["noteoff_chip_frame"],
              "noteon_off_native",r["chip_register_edges"]["native"]["noteon_chip_frame"],
              r["chip_register_edges"]["native"]["noteoff_chip_frame"],
              "duration_delta_frames",r["note_duration_difference_frames"])
        for name,w in r["windows"].items():
            m=w["metrics"]
            print("P234_DRY_WINDOW",r["program"],name,
                  "frames",m["creative"]["frames"],
                  "orig_minus_native_L_dB",m["creative_minus_native_left_rms_db"],
                  "orig_minus_native_R_dB",m["creative_minus_native_right_rms_db"],
                  "envelope_corr",m["envelope_correlation"],
                  "spectral_dB",m["original_minus_native_spectral_bands_db"])
    print("P234_RAW_AUDIO_PRIVATE, NUMERIC_REPORT_ONLY, ZERO_WET_RETURNS_NATIVE,"
          " REAL_ORIGINAL_DRIVER, NO_EQUAL_STATE_PASS")
    return result

def main():
    ap=argparse.ArgumentParser()
    for k in ("original-stage","original-dry","p48","p67","native-root","out"):
        ap.add_argument("--"+k,type=Path,required=True)
    for k in ("original-86box-sha","native-sha","observer-sha"):
        ap.add_argument("--"+k,required=True)
    audit(ap.parse_args())

if __name__=="__main__":
    main()
