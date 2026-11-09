#!/usr/bin/env python3
"""P200: independent pitch-ridge verification of real CT4390 EG1 envelope.

Measures *frequencies*, not louder-harmonic changes, from original AWE64 Gold
analog FLAC and native 86Box, with identical MIDI and SoundFont. Compares 96ms
and 160ms spectral maxima plus autocorrelation, at three predeclared lags
(-23/0/+23ms). P199 inferred the 23ms lag from independent release envelopes.
No DSP modifications, per-note tuning, gain fits, or audio rewriting.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import correlate, find_peaks, resample_poly

from p98_effect_subtests import load_events

RATE = 48000
PHASES = {
    "attack": (10.64, 11.44),
    "hold": (11.68, 12.43),
    "decay": (12.68, 13.43),
    "sustain": (13.68, 14.43),
    "release": (14.66, 15.12),
}
LAGS_MS = (-23, 0, 23)


def cents(a, b):
    return float(1200 * np.log2(max(a, 1e-6) / max(b, 1e-6)))


def peak_freq(mono, time_s, window_s):
    count = int(round(window_s * RATE))
    center = int(round(time_s * RATE))
    data = mono[center - count//2:center - count//2 + count]
    if len(data) != count or np.sqrt(np.mean(data*data)) < 0.0002:
        return None
    w = np.hanning(count)
    spec = abs(np.fft.rfft((data - np.mean(data))*w, n=65536))
    freqs = np.fft.rfftfreq(65536, 1/RATE)
    band = (freqs>=300.) & (freqs<=850.)
    inds = np.flatnonzero(band)
    if inds.size < 10:
        return None
    idx = int(inds[np.argmax(spec[inds])])
    if idx < 1 or idx+1 >= len(spec):
        return None
    lo, mi, hi = np.log(np.maximum(spec[idx-1:idx+2], 1e-12))
    den=lo - 2*mi + hi
    delta=float(np.clip(.5*(lo-hi)/den, -.5,.5)) if abs(den)>1e-8 else 0.
    return (idx+delta)*RATE/65536


def acf_freq(mono, time_s, window_s):
    count=int(round(window_s*RATE))
    center=int(round(time_s*RATE))
    data=mono[center-count//2:center-count//2+count]
    if len(data)!=count or np.sqrt(np.mean(data*data))<0.0002:
        return None
    data=(data-np.mean(data))*np.hanning(count)
    ac=correlate(data,data,mode="full",method="fft")[count-1:]
    lo=int(np.ceil(RATE/850));hi=int(np.floor(RATE/300))
    # The first *strong* period peak prevents high-harmonic octave errors.
    peaks,_=find_peaks(ac[lo:hi+1])
    if len(peaks)==0:
        return None
    candidates=peaks+lo
    vals=ac[candidates]/max(float(ac[0]),1e-12)
    peak=int(candidates[np.argmax(vals)])
    if vals.max()<.22 or peak<1 or peak+1>=len(ac):
        return None
    d0,d1,d2=ac[peak-1:peak+2]
    denom=d0-2*d1+d2
    offset=float(np.clip(.5*(d0-d2)/denom,-.5,.5)) if abs(denom)>1e-10 else 0.
    return RATE/(peak+offset)


def estimate(mono, time_s):
    ps=[peak_freq(mono,time_s,w) for w in (.096,.160)]
    ac=acf_freq(mono,time_s,.096)
    if any(x is None for x in ps) or ac is None:
        return {"valid":False,"peaks_hz":ps,"acf_hz":ac,"reason":"weak or undetermined"}
    spectral_spread=abs(cents(ps[0],ps[1]))
    acf_spread=abs(cents(ps[0],ac))
    # P102 original dominant-peak only was 180ms, which may hide pitch
    # modulation and lock onto a brighter harmonic; independent ACF confirms.
    ok=spectral_spread<=18 and acf_spread<=35
    return {"valid":bool(ok),"pitch_hz":round(float(np.median(ps)),3) if ok else None,
            "peaks_hz":[round(x,3) for x in ps],
            "acf_hz":round(ac,3),
            "spectral_method_spread_cents":round(spectral_spread,2),
            "spectral_vs_acf_cents":round(acf_spread,2),
            "reason":"independent estimators agree" if ok else "harmonic or chirp/window ambiguity"}


def verify_fixture(metadata, events):
    p=[x for x in metadata if x["program"]==0 and x["bank"]==0]
    if len(p)!=1:
        raise ValueError("P200 original public SoundFont program missing")
    linked=[x["generator"]["instrument"] for x in p[0]["preset_zones"]
            if "instrument" in x["generator"] and
            x["generator"].get("keyRange",[0,127])[0]<=59<=x["generator"].get("keyRange",[0,127])[1]]
    voices=[z["generator"] for i in p[0]["instruments"] if i["id"] in linked
            for z in i["zones"] if "sampleID" in z["generator"] and
            z["generator"].get("keyRange",[0,127])[0]<=59<=z["generator"].get("keyRange",[0,127])[1]]
    if len(voices)!=1 or voices[0]["sampleID"]!=43 or voices[0].get("modEnvToPitch")!=1200:
        raise ValueError("P200 expected original single-zone EG1 pitch test #2")
    ons=[x for x in events if x["type"]=="note_on" and x["ch"]==0
         and x["note"]==59 and x["v"]>0 and abs(x["t"]-9.5)<.005]
    offs=[x for x in events if x["ch"]==0 and x["note"]==59
          and abs(x["t"]-14.5)<.005 and (x["type"]=="note_off"
          or x["type"]=="note_on" and x["v"]==0)]
    if len(ons)!=1 or len(offs)!=1:
        raise ValueError("P200 original MIDI envelope fixture not verified")
    return voices[0]


def main():
    ap=argparse.ArgumentParser()
    for name in ("reference","native","events","p97-report","p199-report","sf2-metadata","out"):
        ap.add_argument("--"+name,required=True)
    args=ap.parse_args()
    p97=json.loads(Path(args.p97_report).read_text())
    p199=json.loads(Path(args.p199_report).read_text())
    meta=json.loads(Path(args.sf2_metadata).read_text())
    fixture=verify_fixture(meta,load_events(args.events))
    rel=p199["release"]
    lags=sorted(x["best_analysis_only_lag"]["analysis_lag_ms"] for x in rel)
    if len(lags)!=2 or any(abs(x-23)>2 for x in lags) or p97["compared_seconds"]!=264:
        raise ValueError("P200 requires independently verified P199 lag and P97 full reference")
    hw,sr=sf.read(args.reference,frames=16*RATE,dtype="float32",always_2d=True)
    nat,nr=sf.read(args.native,frames=16*44100,dtype="float32",always_2d=True)
    if (sr,nr)!=(RATE,44100) or hw.shape[1]!=2 or nat.shape[1]!=2:
        raise ValueError("P200 wrong audio formats")
    nat=resample_poly(nat,160,147,axis=0)
    offset=int(round(p97["original_hardware_relative_latency_ms"]*RATE/1000.))
    if offset>=0:
        hw=hw[offset:]
    else:
        nat=nat[-offset:]
    # No per-note gain or pitch normalisation; mean of original two channels
    # is appropriate because both are mono-note sources, pan differences aside.
    hm=np.mean(hw,axis=1,dtype=np.float64)
    nm=np.mean(nat,axis=1,dtype=np.float64)
    rows={}
    for phase,(start,stop) in PHASES.items():
        pts=np.arange(start,stop,0.08)
        all_rows=[]
        for tm in pts:
            h=estimate(hm,float(tm))
            combos={}
            for lag in LAGS_MS:
                n=estimate(nm,float(tm+lag/1000.))
                valid=h["valid"] and n["valid"]
                combos[str(lag)]={"valid":bool(valid),"native":n,
                     "native_minus_hardware_cents":round(cents(n["pitch_hz"],h["pitch_hz"]),2)
                     if valid else None}
            all_rows.append({"time_s":round(float(tm),3),"hardware":h,"lags":combos})
        metrics={}
        for lag in LAGS_MS:
            diffs=[r["lags"][str(lag)]["native_minus_hardware_cents"] for r in all_rows
                   if r["lags"][str(lag)]["valid"]]
            metrics[str(lag)]={"matched_bins":len(diffs),
                "median_signed_cents":round(float(np.median(diffs)),2) if diffs else None,
                "median_absolute_cents":round(float(np.median(np.abs(diffs))),2) if diffs else None,
                "p90_absolute_cents":round(float(np.percentile(np.abs(diffs),90)),2) if diffs else None}
            if lag==0 and len(diffs)<4:
                raise ValueError("P200 pitch estimator does not validate enough "+phase+" bins")
        rows[phase]={"time_range_s":[start,stop],"metrics":metrics,"measurements":all_rows}
        print("P200 %-8s independent-frequency bins %d/%d; median error cents (lag -23/0/+23): %s" %
              (phase,metrics["0"]["matched_bins"],len(pts),
               [(k,metrics[k]["median_signed_cents"],metrics[k]["median_absolute_cents"])
                for k in ("-23","0","23")]))
    hold=rows["hold"]["metrics"]["0"]
    sustain=rows["sustain"]["metrics"]["0"]
    if hold["median_absolute_cents"]>25 or sustain["median_absolute_cents"]>25:
        raise ValueError("P200 stable notes contradict original P102 reference; cannot certify tracker")
    output={"experiment":"P200 independent EG1-to-pitch hardware-vs-native estimator audit",
      "reference":"original CT4390 analog line out FLAC 48kHz, original SF2/MIDI",
      "p97_coarse_lag_ms":p97["original_hardware_relative_latency_ms"],
      "original_p199_release_only_common_lag_ms":23,
      "sf2_fixture":fixture,
      "estimators":"2 FFT peak windows 96/160ms plus normalized 96ms autocorrelation; reject >18c spectral or >35c ACF mismatch",
      "lag_scan_fixed_ms":list(LAGS_MS),
      "phases":rows,
      "limits":["Only one original SF2 test note 59; cannot infer all EG1 usage.",
       "Pitch-spectrum tracker can be distorted by sample harmonic and filter coloration; rejected bins are not signal proof.",
       "Lags are post-hoc analysis only and cannot be changed in audio processing.",
       "Independent real EMU8000 hardware modulation-register snapshots unavailable.",
       "No DSP code changes, reference FLAC and pinned MIDI/SF2 unchanged."]}
    Path(args.out).write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
