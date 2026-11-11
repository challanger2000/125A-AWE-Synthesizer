#!/usr/bin/env python3
"""P230 numeric ROM/SBK A/B: native PCM versus independently captured Creative Win95 PCM.
No gain normalization. WAV labels cannot establish original-driver provenance.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import tempfile
import wave
from pathlib import Path
import numpy as np

RATE=44100
HOP=441
BANDS=((80,250),(250,1000),(1000,4000),(4000,10000),(10000,20000))
FIELDS={"file","bank","program","note","velocity","channel","voices","nonzero","rails"}

def read_wav(path:Path)->np.ndarray:
    if not path.is_file():
        raise ValueError(f"missing WAV: {path}")
    with wave.open(str(path),"rb") as reader:
        if (reader.getnchannels()!=2 or reader.getframerate()!=RATE or
            reader.getsampwidth()!=2 or reader.getcomptype()!="NONE"):
            raise ValueError(f"{path}: expected 44.1kHz stereo signed PCM16")
        count=reader.getnframes()
        if not RATE<=count<=RATE*6:
            raise ValueError(f"{path}: implausible frame length")
        data=reader.readframes(count)
    if len(data)!=count*4:
        raise ValueError(f"{path}: truncated PCM")
    return np.frombuffer(data,dtype="<i2").reshape(-1,2).copy()

def envelope(pcm:np.ndarray)->np.ndarray:
    mono=pcm.mean(axis=1,dtype=np.float64)/32768.
    n=len(mono)//HOP
    if n<100: raise ValueError("audio too short")
    return np.sqrt(np.mean(mono[:n*HOP].reshape(n,HOP)**2,axis=1))

def lag(reference:np.ndarray,native:np.ndarray)->tuple[int,float]:
    a,b=envelope(reference),envelope(native)
    a-=np.mean(a);b-=np.mean(b)
    if np.linalg.norm(a)<1e-9 or np.linalg.norm(b)<1e-9:
        return 0,0.
    shifts=np.arange(-20,21)
    scores=[]
    for offset in shifts:
        if offset>=0:
            x,y=a[offset:],b[:len(a)-offset]
        else:
            x,y=a[:len(b)+offset],b[-offset:]
        size=min(len(x),len(y))
        x,y=x[:size],y[:size]
        denom=np.linalg.norm(x)*np.linalg.norm(y)
        scores.append(float(x.dot(y)/denom) if denom else -1.)
    index=int(np.argmax(scores))
    return int(shifts[index]*10),float(scores[index])

def align(reference:np.ndarray,native:np.ndarray,delay_ms:int)->tuple[np.ndarray,np.ndarray]:
    offset=delay_ms*RATE//1000
    if offset>0: reference=reference[offset:]
    elif offset<0: native=native[-offset:]
    n=min(len(reference),len(native))
    if n<RATE: raise ValueError("aligned audio below one second")
    return reference[:n].astype(np.float64)/32768.,native[:n].astype(np.float64)/32768.

def db(x:float)->float:
    return 20*math.log10(x) if x>1e-12 else -240.

def bands(pcm:np.ndarray)->dict[str,float]:
    mono=np.mean(pcm,axis=1)
    n=4096
    if len(mono)<n: raise ValueError("spectrum needs >4096 frames")
    frames=np.lib.stride_tricks.sliding_window_view(mono,n)[::2048]
    power=(np.abs(np.fft.rfft(frames*np.hanning(n),axis=1))**2).mean(axis=0)
    bins=np.fft.rfftfreq(n,1/RATE)
    return {f"{lo}-{hi}Hz":float(power[(bins>=lo)&(bins<hi)].sum())
            for lo,hi in BANDS}

def compare_pair(ref_path:Path,native_path:Path)->dict:
    reference,native=read_wav(ref_path),read_wav(native_path)
    if not np.any(reference) or not np.any(native):
        raise ValueError(f"silent reference or native PCM: {ref_path.name}")
    delay,corr=lag(reference,native)
    r,n=align(reference,native,delay)
    rr,nn=float(np.sqrt(np.mean(r**2))),float(np.sqrt(np.mean(n**2)))
    b1,b2=bands(r),bands(n)
    difference={k:round(10*math.log10(max(b1[k],1e-25)/max(b2[k],1e-25)),2)
                for k in b1}
    rrails=int(np.count_nonzero((r>=32767/32768)|(r<=-1)))
    nrails=int(np.count_nonzero((n>=32767/32768)|(n<=-1)))
    gain=round(db(rr)-db(nn),3)
    flags=[]
    if abs(gain)>.5: flags.append("rms_difference_above_0.5dB")
    if corr<.97: flags.append("envelope_correlation_below_0.97")
    if max(abs(v) for v in difference.values())>1.: flags.append("band_difference_above_1dB")
    if abs(rrails-nrails)>10: flags.append("rail_count_difference")
    return {"reference_later_than_native_ms":delay,
            "envelope_correlation":round(corr,5),
            "aligned_frames":len(r),
            "reference_rms_dbfs":round(db(rr),3),
            "native_rms_dbfs":round(db(nn),3),
            "reference_minus_native_rms_db":gain,
            "reference_peak_dbfs":round(db(float(np.max(np.abs(r)))),3),
            "native_peak_dbfs":round(db(float(np.max(np.abs(n)))),3),
            "reference_rail_samples":rrails,
            "native_rail_samples":nrails,
            "reference_minus_native_bands_db":difference,
            "flags":flags,
            "classification":"REVIEW" if flags else "NUMERICALLY_CLOSE_NOT_HARDWARE_PROOF"}

def load_matrix(folder:Path)->list[dict]:
    source=folder/"cases.csv"
    if not source.is_file(): raise ValueError("native cases.csv missing")
    with source.open(newline="",encoding="utf-8") as f:
        reader=csv.DictReader(f)
        if not FIELDS<=set(reader.fieldnames or []):
            raise ValueError("case manifest missing required columns")
        rows=list(reader)
    names=[row["file"] for row in rows]
    if len(rows)!=397 or len(set(names))!=397:
        raise ValueError("expected full 397 unique ROM/SBK cases")
    for row in rows:
        if (Path(row["file"]).name!=row["file"] or
            Path(row["file"]).suffix.lower()!=".wav" or
            int(row["bank"]) not in (16382,16383)):
            raise ValueError("invalid ROM/SBK case path or bank")
    return rows

def audit(original:Path,native:Path,out:Path)->dict:
    cases=load_matrix(native)
    expected={row["file"] for row in cases}
    for label,root in (("original",original),("native",native)):
        got={p.name for p in root.glob("*.wav")}
        if got!=expected:
            raise ValueError(f"{label}: missing={sorted(expected-got)[:5]} extra={sorted(got-expected)[:5]}")
    details,alerts={},[]
    for row in cases:
        filename=row["file"]
        data=compare_pair(original/filename,native/filename)
        details[filename]=data
        if data["flags"]:
            alerts.append({"file":filename,"flags":data["flags"],
                           "rms_difference_db":data["reference_minus_native_rms_db"]})
    report={"schema":"125A-P230-ROM-SBK-A-B-v1",
            "note":"WAV names cannot prove original Creative origin. Verify Creative Win95 driver, original asset hashes, mixer/FX settings independently. This is not physical AWE64 silicon/audio parity.",
            "total_pairs":len(cases),"flagged_pairs":len(alerts),
            "original_driver_provenance":"NOT INDEPENDENTLY VERIFIED BY THIS TOOL",
            "release":"BLOCKED","discrepancies":alerts,"pairs":details,
            "native_matrix_sha256":hashlib.sha256((native/"cases.csv").read_bytes()).hexdigest()}
    if out.exists(): raise ValueError("refuse overwrite of prior acoustic evidence")
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report

def emit(path:Path,samples:np.ndarray)->None:
    with wave.open(str(path),"wb") as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(RATE)
        w.writeframes(samples.astype("<i2").tobytes())

def selftest():
    with tempfile.TemporaryDirectory(prefix="p230-ab-") as temp:
        a,b=Path(temp)/"a.wav",Path(temp)/"b.wav"
        t=np.arange(RATE*2)/RATE
        env=np.minimum(1,np.maximum(0,(t-.07)*100))*np.where(t<1,1,np.exp(-4*(t-1)))
        s=(11000*env*np.sin(2*np.pi*440*t)).astype("<i2")
        both=np.column_stack([s,s])
        emit(a,both);emit(b,both)
        control=compare_pair(a,b)
        assert control["flags"]==[] and control["reference_minus_native_rms_db"]==0,control
        emit(b,np.column_stack([s//2,s//2]))
        mutant=compare_pair(a,b)
        assert "rms_difference_above_0.5dB" in mutant["flags"],mutant
        assert "band_difference_above_1dB" in mutant["flags"],mutant
        with wave.open(str(b),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE)
            w.writeframes(s.tobytes())
        try: compare_pair(a,b)
        except ValueError: pass
        else: raise AssertionError("mono input incorrectly accepted")
    print("P230_ROM_SBK_AB_SELFTEST_PASS identical, gain_mutant, invalid_format")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--reference-dir",type=Path)
    p.add_argument("--native-dir",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.self_test: return selftest()
    if not(args.reference_dir and args.native_dir and args.out):
        p.error("--reference-dir --native-dir --out required")
    result=audit(args.reference_dir,args.native_dir,args.out)
    print(f"P230 measured {result['total_pairs']} WAV pairs; flagged {result['flagged_pairs']};"
          " ORIGINAL_DRIVER_PROVENANCE=NOT_VERIFIED RELEASE=BLOCKED")

if __name__=="__main__":main()
