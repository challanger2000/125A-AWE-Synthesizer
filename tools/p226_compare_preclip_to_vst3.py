#!/usr/bin/env python3
"""P226: audit raw signed32 chip output against a *separate* P222 VST3 WAV.

No transformation of the SF2, chip, VST3 or user media. The P222 Float32
wave is itself derived from an already signed16-clipped EMU8000 signal;
we check native clip(raw32) against it. No physical Creative parity claim.
Standard library only; usable in the offline evaluator.
"""
import argparse
import array
import json
import math
from pathlib import Path
import struct
import sys
import zipfile

FRAMES = 132300
SAMPLES = FRAMES * 2

def signed16(value):
    return max(-32768, min(32767, value))

def parse_raw32(data):
    if len(data) != SAMPLES*4:
        raise ValueError(f"wrong P226 signed32 capture length: {len(data)}")
    if sys.byteorder != "little":
        # array('i') uses native order; reject instead of misreading.
        raise ValueError("P226 raw32le requires little-endian host")
    data32 = array.array("i")
    data32.frombytes(data)
    if data32.itemsize != 4 or len(data32) != SAMPLES:
        raise ValueError("P226 requires 32-bit signed integer capture")
    return data32

def parse_f32_wav(blob):
    if len(blob) != 44 + SAMPLES*4:
        raise ValueError(f"wrong P222 IEEE-float WAV length: {len(blob)}")
    if (blob[:4],blob[8:12],blob[12:16],blob[36:40]) != (
        b"RIFF",b"WAVE",b"fmt ",b"data"):
        raise ValueError("P222 WAV invalid RIFF chunks")
    (fmt,channels,rate,byte_rate,align,bits) = struct.unpack_from(
        "<HHIIHH",blob,20)
    if (fmt,channels,rate,byte_rate,align,bits) != (
        3,2,44100,352800,8,32):
        raise ValueError("P222 WAV is not actual stereo 44100 Hz IEEE-float32")
    (data_bytes,) = struct.unpack_from("<I",blob,40)
    if data_bytes != SAMPLES*4:
        raise ValueError("P222 WAV incomplete data chunk")
    wav = array.array("f")
    wav.frombytes(blob[44:])
    if wav.itemsize != 4:
        raise ValueError("P222 float32 host unsupported")
    for v in wav:
        if not math.isfinite(v) or not (-1 <= v <= 32767/32768):
            raise ValueError("P222 WAV has nonfinite or out-of-PCM16-grid values")
        if v*32768 != round(v*32768):
            raise ValueError("P222 WAV is not the previously clipped signed16 signal")
    return wav

def compare(raw, wav):
    if len(raw)!=SAMPLES or len(wav)!=SAMPLES:
        raise ValueError("P226/P222 sample count mismatch")
    mismatches=0
    first=-1
    max_error=0.0
    summed=0.0
    native_excess_negative=0
    native_excess_positive=0
    for i,(v,s) in enumerate(zip(raw,wav)):
        expected=signed16(v)/32768.0
        delta=expected - s
        if delta != 0:
            mismatches+=1
            if first<0:first=i
        max_error=max(max_error,abs(delta))
        summed+=delta*delta
        native_excess_negative+=v<-32768
        native_excess_positive+=v>32767
    return {
        "matched_samples":SAMPLES-mismatches,
        "mismatched_samples":mismatches,
        "first_mismatch_frame":first//2 if first>=0 else None,
        "first_mismatch_channel":first%2 if first>=0 else None,
        "max_abs_error":max_error,
        "rms_error":math.sqrt(summed/SAMPLES),
        "native_overflow_negative":native_excess_negative,
        "native_overflow_positive":native_excess_positive,
        "native_truly_preclip_peak":max(abs(min(raw)),abs(max(raw)))/32768.0,
        "byte_exact_after_clamp":mismatches==0,
    }

def self_test():
    baseline=array.array("i",[0]*SAMPLES)
    baseline[0]=-65536
    baseline[1]=70000
    baseline[102]=-1234
    wav=array.array("f",[signed16(v)/32768 for v in baseline])
    answer=compare(baseline,wav)
    assert answer["byte_exact_after_clamp"]
    assert answer["native_overflow_negative"]==1
    assert answer["native_overflow_positive"]==1
    assert answer["native_truly_preclip_peak"]==70000/32768
    wav[102]=0
    wrong=compare(baseline,wav)
    assert wrong["mismatched_samples"]==1 and wrong["first_mismatch_frame"]==51
    assert wrong["byte_exact_after_clamp"] is False
    # An incorrect raw file length and non-PCM16 reference must be rejected.
    for invalid in (b"\x00"*4,b""):
        try: parse_raw32(invalid)
        except ValueError: pass
        else: raise AssertionError("truncated raw32 false pass")
    fake=bytearray(44+SAMPLES*4)
    try:parse_f32_wav(fake)
    except ValueError:pass
    else:raise AssertionError("invalid RIFF falsely accepted")
    print("P226_COMPARATOR_POSITIVE_AND_MUTATION_PASS; no real VST3/Creative parity")

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--raw-dir",type=Path)
    ap.add_argument("--p222-zip",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.self_test:
        self_test();return 0
    if not(args.raw_dir and args.p222_zip and args.out):
        ap.error("--raw-dir, --p222-zip and --out are all required")
    result={"scope":"P226 NATIVE INT32 PRECLIP versus P222 REAL EXPORTED VST3 CLIPPED F32",
            "original_creative_comparison":"NOT_RUN","release":"BLOCKED",
            "cases":[]}
    with zipfile.ZipFile(args.p222_zip) as capture:
        for program in (0,21):
            for note,velocity in ((48,64),(72,120)):
                for stage in ("DRY","REVERB","CHORUS","BOTH"):
                    label=f"P{program:03d}-N{note}V{velocity}-{stage}"
                    rawpath=args.raw_dir/(label+".raw32le")
                    raw=parse_raw32(rawpath.read_bytes())
                    wavnames=[n for n in capture.namelist()
                              if n.endswith("/"+label+"-ACTUAL-VST3-F32.wav") or
                                 n==label+"-ACTUAL-VST3-F32.wav"]
                    if len(wavnames)!=1:
                        raise ValueError("missing/non-unique P222 VST3 source WAV: "+label)
                    wav=parse_f32_wav(capture.read(wavnames[0]))
                    result["cases"].append({"label":label,**compare(raw,wav)})
    if len(result["cases"])!=16:
        raise ValueError("P226 must compare all sixteen actual cases")
    result["exact_cases"]=sum(x["byte_exact_after_clamp"] for x in result["cases"])
    result["native_preclip_verified"]=True
    result["vst3_full_pcm_parity"]=result["exact_cases"]==16
    result["conclusion"]=(
      "Native 32-bit output and separately recorded VST3 16-bit-limited output align"
      if result["vst3_full_pcm_parity"] else
      "Native 32-bit output disagrees with one or more actual VST3 captures;"
      " investigate engine state, sample offsets or master gain before sound attribution")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(f"P226_PRIVATE_SF2_AB: {result['exact_cases']}/16 sample-exact after clamp;"
          " original Creative reference still NOT_RUN")
    return 0 if result["vst3_full_pcm_parity"] else 1

if __name__=="__main__":
    try:sys.exit(main())
    except (ValueError,OSError,zipfile.BadZipFile) as e:
        print("P226_INVALID_EVIDENCE:",e,file=sys.stderr)
        sys.exit(2)
