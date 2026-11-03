#!/usr/bin/env python3
"""P87: compare six independent original-Creative and native EMU8000 captures.

No 1:1 fidelity is inferred from two copies of the native recording. An actual
P67 Windows-95 guest driver report is required, and comparison remains a
diagnostic rather than a physical-hardware-parity claim.
Requires numpy. Never reads or uploads the original SF2/sample payload.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import wave
from pathlib import Path
import numpy as np

NOTES={(0,36):"StandardStuff Kick",(0,38):"StandardStuff Snare",
       (0,42):"StandardStuff Hi-Hat",(17,36):"Industrial Kick",
       (17,38):"Industrial Snare",(17,42):"Industrial Hi-Hat"}
BANDS=(20,80,160,320,640,1280,2560,5120,10240,20000)

def read_wav(path):
    with wave.open(str(path),"rb") as f:
        spec=(f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getcomptype())
        if spec!=(2,2,44100,"NONE"):
            raise ValueError(f"{path.name}: expected 44.1kHz PCM16 stereo, found {spec}")
        if f.getnframes()<22050:raise ValueError("Capture shorter than 0.5 seconds")
        data=np.frombuffer(f.readframes(f.getnframes()),dtype="<i2")
    if not np.any(data):raise ValueError("Silent WAV: "+path.name)
    return data.reshape((-1,2)).astype(np.float64)/32768.

def onset(pcm):
    n=220
    blocks=len(pcm)//n
    envelope=np.sqrt((pcm[:blocks*n].reshape((blocks,n,2))**2).mean(axis=(1,2)))
    points=np.flatnonzero(envelope>=max(0.00005,float(envelope.max())*0.08))
    if not len(points):raise ValueError("No usable note onset")
    return int(points[0]*n)

def spectrum(pcm,attack):
    i=max(0,min(attack+512,len(pcm)-8192))
    mono=pcm[i:i+8192].mean(axis=1)
    if len(mono)<8192:mono=np.pad(mono,(0,8192-len(mono)))
    fft=np.fft.rfft(mono*np.hanning(8192))
    frequency=np.fft.rfftfreq(8192,1/44100)
    energy=np.abs(fft)**2
    bands=np.array([float(energy[(frequency>=a)&(frequency<b)].sum())
                    for a,b in zip(BANDS[:-1],BANDS[1:])])
    return (10*np.log10((bands+1e-20)/(bands.sum()+1e-20))).tolist()

def compare(reference,native):
    reference=Path(reference);native=Path(native)
    if hashlib.sha256(reference.read_bytes()).digest()==hashlib.sha256(native.read_bytes()).digest():
        raise ValueError("Duplicate WAV: an independent Creative Win95 reference was not supplied")
    a=read_wav(reference);b=read_wav(native)
    ai=onset(a);bi=onset(b)
    frames=min(len(a)-ai,len(b)-bi,44100)
    if frames<8192:raise ValueError("Too little audio after note-on")
    wave_a=a[ai:ai+frames].mean(axis=1)
    wave_b=b[bi:bi+frames].mean(axis=1)
    best=(-2.,0,0.)
    for shift in range(-128,129,8):
        if shift>=0:x=wave_a[shift:];y=wave_b[:len(x)]
        else:y=wave_b[-shift:];x=wave_a[:len(y)]
        ex=float(x@x);ey=float(y@y)
        if ex<=1e-12 or ey<=1e-12:continue
        corr=float((x@y)/np.sqrt(ex*ey))
        if corr>best[0]:best=(corr,shift,float((x@y)/ey))
    correlation,shift,gain=best
    if correlation< -1:raise ValueError("No usable correlation window")
    if shift>=0:x=wave_a[shift:];y=wave_b[:len(x)]
    else:y=wave_b[-shift:];x=wave_a[:len(y)]
    rmsa=float(np.sqrt((x*x).mean()))
    rmsb=float(np.sqrt((y*y).mean()))
    residual=float(np.sqrt(((x-gain*y)**2).mean()))
    spec_a=spectrum(a,ai);spec_b=spectrum(b,bi)
    db=lambda n:20*np.log10(n+1e-16)
    return {"original":reference.name,"native":native.name,
            "rms_original_dbfs":round(float(db(rmsa)),2),
            "rms_native_dbfs":round(float(db(rmsb)),2),
            "level_difference_db":round(float(db(rmsa)-db(rmsb)),2),
            "waveform_correlation":round(correlation,5),
            "sample_alignment_frames":shift,
            "original_onset_ms":round(ai/44.1,2),
            "native_onset_ms":round(bi/44.1,2),
            "normalized_residual_db":round(float(db(residual)-db(rmsa)),2),
            "spectrum_difference_db_by_band":
                [round(abs(x-y),2) for x,y in zip(spec_a,spec_b)],
            "band_edges_hz":BANDS,"physical_hardware_1to1_proven":False}

def compare_directory(reference_dir,native_dir):
    results=[]
    for (program,note),name in NOTES.items():
        originals=list(Path(reference_dir).glob(f"*P{program}*N{note}*.wav"))
        natives=list(Path(native_dir).glob(f"*P{program}*N{note}*.wav"))
        if len(originals)!=1 or len(natives)!=1:
            raise ValueError(f"{name}: need exactly one independently captured WAV per backend")
        item=compare(originals[0],natives[0])
        item.update({"program":program,"note":note,"name":name})
        results.append(item)
    return results

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--creative-dir",required=True,type=Path)
    parser.add_argument("--native-dir",required=True,type=Path)
    parser.add_argument("--p67-guest-report",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args()
    guest=json.loads(args.p67_guest_report.read_text(encoding="utf8"))
    if not (guest.get("agent_launched_in_actual_win95")
            and guest.get("original_creative_winmm_endpoint_selected")
            and guest.get("p75_sf2_sample_upload_plausible")):
        raise ValueError("Original Creative Win95 SoundFont load / MIDI route not established")
    comparisons=compare_directory(args.creative_dir,args.native_dir)
    result={"phase":"P87","independent_win95_driver_report_verified":True,
            "six_auditions_measured":len(comparisons),"comparisons":comparisons,
            "physical_hardware_parity_proven":False,
            "verdict":"MEASUREMENTS ONLY – requires genuine AWE64 hardware recording for physical parity"}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("P87 measured",len(comparisons),"original Creative Win95 vs native EMU8000 WAV pairs")

if __name__=="__main__":
    main()
