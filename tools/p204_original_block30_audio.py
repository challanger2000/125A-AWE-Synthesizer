#!/usr/bin/env python3
"""P204: extract the *actual* Sound Blaster AWE32 AWETST25 Block30 mod-envelope
brightness time series (8 hardware chip rates, not simulated audio).
Sources: hash-pinned original recordings/recc138..140 FLAC and AWETEST.LOG.
Raw capture is internally routed and non-linear: brightness is a proxy,
NOT the silicon envelope itself. No DSP modifications or extracted samples
are uploaded. Report only derived time-frequency statistics.
"""
import argparse
import json
import re
from pathlib import Path
import numpy as np
import soundfile as sf

RATES=(0x10,0x14,0x18,0x20,0x24,0x2c,0x34,0x3c)
CAPFILE={2311859:"recc138.flac",2329859:"recc139.flac",2346259:"recc140.flac"}
SR=44100
N=256
HOP=220
FRAC=(.05,.1,.2,.3,.4,.5,.6,.8)
SOURCES={
 "recc138.flac":"f85f601bede930aa93b5670d4981800d56f21669",
 "recc139.flac":"08fb1bb284e8f71da44c8607fef996e67feb293",
 "recc140.flac":"c7d220dddda348be0571f35b7642319230b04b28",
}

def divisor(r):
    group,mant=(r>>4)&7,r&15
    return (mant+1) if group==0 else (mant+17) << (group-1)

def moments(y, frame):
    # Keep the capture phase exactly in the AWETEST log. Do not optimise a
    # separate onset shift for each rate: it would favour one envelope model.
    dur=1.65
    start=frame
    clip=y[start:start+int(dur*SR)]
    if len(clip)<int(1.55*SR):
        raise ValueError("P204 insufficient hardware audio for start frame "+str(frame))
    window=np.hanning(N)
    fq=np.fft.rfftfreq(N,1/SR)
    hi=(fq>=3000)&(fq<12000)
    lo=(fq>=200)&(fq<1500)
    if not (hi.sum() and lo.sum()):
        raise ValueError("Invalid FFT frequency bins")
    samples=[];times=[]
    for pos in range(0,len(clip)-N,HOP):
        chunk=clip[pos:pos+N].astype(np.float64)
        p=np.abs(np.fft.rfft(chunk*window))**2
        bright=10*np.log10((p[hi].sum()+1e-12)/(p[lo].sum()+1e-12))
        times.append((pos+N/2)/SR)
        samples.append(bright)
    t=np.asarray(times)
    b=np.asarray(samples)
    # Approximate original AWETST analysis smoothing 5*5ms.
    bs=np.convolve(b,np.ones(5)/5,mode="same")
    # fixed, post-attack note plateau; no fitting of phase or nonlinear
    # brightness->modulation conversion.
    plateau=float(np.median(bs[(t>=1.15)&(t<=1.45)]))
    return t,bs,plateau

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--log",required=True)
    ap.add_argument("--recordings",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    contents=Path(args.log).read_text(errors="replace")
    rex=re.compile(r"^\s*\d+\s+30 mod attack 0x([0-9A-Fa-f]{2})\s+@rt\s+\d+:\d+\s+cap\s+(\d+):(\d+)",re.M)
    events={}
    for raw,cap,frame in rex.findall(contents):
        rate=int(raw,16)
        if rate in events:
            raise ValueError("Duplicate original AWETST block30 rate")
        events[rate]=(int(cap),int(frame))
    if tuple(sorted(events))!=RATES:
        raise ValueError("Missing/reordered original AWETST chip attack rates: "+repr(sorted(events)))
    raw={}
    for filename in sorted(CAPFILE.values()):
        path=Path(args.recordings)/filename
        with sf.SoundFile(path) as f:
            if f.samplerate!=SR or f.frames<300_000:
                raise ValueError("Unexpected original hardware FLAC "+filename)
            data=f.read(dtype="float32",always_2d=True)
        if data.shape[1] not in (1,2):
            raise ValueError("Unsupported original capture channels")
        raw[filename]=data[:,0]
    row=[]
    for rate in RATES:
        cap,frame=events[rate]
        if cap not in CAPFILE:
            raise ValueError("Unknown raw original card capture timestamp "+str(cap))
        name=CAPFILE[cap]
        t,b,plateau=moments(raw[name],frame)
        T=11.878/divisor(rate-1) # exact historical AWE32Emu analysis
        brightness={}
        for fraction in FRAC:
            brightness[str(fraction)]=round(float(np.interp(fraction*T,t,b)-plateau),3)
        row.append({
          "hardware_attack_rate_hex":hex(rate),
          "original_capture_file":name,
          "original_capture_start_frame":frame,
          "attack_duration_from_original_emu8000_analysis_seconds":round(T,6),
          "post_attack_brightness_plateau_db":round(plateau,3),
          "brightness_db_vs_plateau_by_normalized_t_over_T":brightness
        })
        print("P204 genuine AWETST25 rate=0x%02X duration T=%.3fs internal high/low brightness vs plateau: "%(rate,T),
              [(f,brightness[str(f)]) for f in (.05,.1,.2,.4,.8)])
    cross_rate={}
    for f in FRAC:
        vals=np.array([r["brightness_db_vs_plateau_by_normalized_t_over_T"][str(f)] for r in row])
        cross_rate[str(f)]={"median_relative_brightness_db":round(float(np.median(vals)),3),
                            "min_db":round(float(vals.min()),3),
                            "max_db":round(float(vals.max()),3),
                            "mad_around_median_db":round(float(np.median(np.abs(vals-np.median(vals)))),3)}
    out={
      "experiment":"P204 read-only independent ORIGINAL AWE32 AWETST25 Block30 audio sanity",
      "real_hardware":"Sound Blaster AWE32 DSP 4.13; 2026-09-12 genuine internal capture, sample clock 44100",
      "upstream_pinned_sources_branch_commit":"9ae2217b92af72f706c9631679cd43c3afff507f",
      "original_capture_flac_git_blob_shas":SOURCES,
      "hardware_block30_attack_register_rates":[hex(x) for x in RATES],
      "slow_creative_win95_sf2_register_0x0C_is_physically_covered":False,
      "brightness_definition":"10log10 energy [3000,12000]Hz / [200,1500]Hz, 256pt Hann, 220 sample hop and 5-window mean",
      "brightness_reference":"own fixed 1.15-1.45s post-attack level per note; only relative timbre, not amplitude",
      "phases_normalised_to_original_reg_attack_duration":list(FRAC),
      "original_real_card_notes":row,
      "cross_rate_deviation":cross_rate,
      "limits":[
        "Original AWE32 internal DMA capture is nonlinear/compressive, particularly for loud material; NOT calibrated to physical mod envelope value.",
        "All original Block30 notes route modulation to FILTER cutoff using noise; the independent CT4390 SF2 note59 routes modulation to PITCH and uses a different physical card.",
        "Short 256-point FFT and 25ms smoothing make the fastest-rate early 5%/10% bins resolution-limited.",
        "The slow 0x0C register has NO original AWETST25 measurement; extrapolating shape beyond 0x10..0x3C remains a hypothesis.",
        "This diagnostic does not identify native-vs-real error: no matched direct-chip render for these individual AWETST25 notes is used.",
        "Original FLAC bytes and AWETEST log are NOT uploaded as artifact."
      ],
      "production_code_change":"NONE"
    }
    Path(args.out).write_text(json.dumps(out,indent=2)+"\n")
    print("P204 PASS: analyzed 8 independent *real hardware* chip-register attack-rate records; NOT an extrapolated rate 0x0C capture")

if __name__=="__main__":
    main()
