#!/usr/bin/env python3
"""P209: Test late native EG1 PCM, using real 86Box engine and P207 driver oracle."""
import argparse, hashlib, json, wave
from pathlib import Path
from p208_creative_register_compare import group

RATE=44100
TOTAL=242550
EARLY=RATE*2
def require(ok,why):
    if not ok: raise ValueError("P209 FAIL: "+why)
def compare(a,b):
    require(len(a)==len(b)==TOTAL*4,"stereo PCM16 length")
    require(a[:EARLY*4]==b[:EARLY*4],"0..2s early attack PCM changed")
    changes=[i for i in range(TOTAL) if a[i*4:i*4+4]!=b[i*4:i*4+4]]
    require(len(changes)>1000,"late-phase effect absent or a single glitch")
    first=changes[0]
    require(int(2.6*RATE)<first<int(4.1*RATE),
            "change was before expected hold/decay or too late")
    regions=[]
    for lo,hi in ((0,2),(2,3),(3,4),(4,5)):
        n=sum(lo*RATE<=x<hi*RATE for x in changes)
        regions.append({"seconds":[lo,hi],"different_stereo_frames":n})
    require(regions[2]["different_stereo_frames"]>0,"no changed frames 3..4s")
    return first,len(changes),regions
def read(path):
    with wave.open(str(path),"rb") as w:
        require((w.getframerate(),w.getnchannels(),w.getsampwidth(),
                 w.getnframes(),w.getcomptype())==
                (44100,2,2,242550,"NONE"),"wrong 5.5s WAV metadata")
        return w.readframes(w.getnframes())
def selftest():
    dry=bytes(TOTAL*4)
    wet=bytearray(dry)
    wet[3*RATE*4:3*RATE*4+3000*4]=b"\x01\x00\x01\x00"*3000
    first,n,_=compare(dry,bytes(wet))
    require(first==3*RATE and n==3000,"positive late-phase fixture")
    for bad in (dry,bytes(b"\x01"+wet[1:]),
                dry[:3*RATE*4]+b"\x01\x00\x01\x00"+dry[3*RATE*4+4:]):
        try: compare(dry,bad)
        except ValueError: pass
        else: raise ValueError("P209 negative mutant not rejected")
    print("P209 synthetic self-test PASS; 3 negative mutants rejected")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    for name in ("fixture","baseline_trace","candidate_trace","baseline_wav","candidate_wav","out"):
        p.add_argument("--"+name.replace("_","-"),dest=name)
    o=p.parse_args()
    if o.self_test:
        selftest()
        if not o.fixture:return
    require(all(getattr(o,n) for n in ("fixture","baseline_trace","candidate_trace",
                                     "baseline_wav","candidate_wav","out")),"missing inputs")
    ref=json.loads(Path(o.fixture).read_text())
    require(ref["schema"]=="P208-real-original-Creative-note59-v1" and
            ref["provenance"]["run"]==42705889086 and
            ref["provenance"]["sf2_git_blob"]==
              "4768c4a0215abf49c7a2bb51ada5ba3494faa1c5",
            "wrong authenticated P207 original driver reference")
    original,n0=group(o.baseline_trace)
    candidate,n1=group(o.candidate_trace)
    require((n0,n1,len(original),len(candidate))==(47,47,32,32),
            "P207 register population not reproduced")
    require(sorted(k for k in original if original[k]!=candidate[k])==
            ["ATKHLD","DCYSUS"],"unexpected register difference")
    for key in ("ATKHLD","DCYSUS","IP","ENVVAL","PEFE"):
        require(original[key]==ref["native_initial"][key],"baseline "+key)
    for key in ("ATKHLD","DCYSUS","ENVVAL","PEFE"):
        require(candidate[key]==ref["original"][key],"creative candidate "+key)
    require(candidate["IP"]==original["IP"],"IP mismatch hidden")
    before,after=read(o.baseline_wav),read(o.candidate_wav)
    first,changed,regions=compare(before,after)
    out={
      "phase":"P209 native 86Box original SF2 EG1 after attack",
      "original_creative_register_oracle_run":42705889086,
      "physical_AWE64_silicon_measurement":"NOT RUN",
      "duration_seconds":5.5,"frames":TOTAL,
      "first_2s_pcm_bit_identical":True,
      "first_changed_frame":first,
      "first_changed_time_seconds":round(first/RATE,6),
      "total_different_stereo_frames":changed,
      "regions":regions,
      "original_pcm_sha256":hashlib.sha256(before).hexdigest(),
      "candidate_pcm_sha256":hashlib.sha256(after).hexdigest(),
      "only_changed_register_series":["ATKHLD","DCYSUS"],
      "creative_IP_register_deviation_remains":True,
      "original_CT4390_pitch_attack_81_85_cents_issue_fixed":False,
      "shipping_product_DSP":"UNCHANGED",
      "release":"NO-GO"
    }
    Path(o.out).write_text(json.dumps(out,indent=2)+"\n")
    print("P209 PASS: first changed actual native stereo PCM frame",first,
          "at",round(first/RATE,6),"seconds; total different",changed)
    print("P209 0..2s attack PCM bit-identical; physical silicon fidelity remains UNVERIFIED")
if __name__=="__main__":
    main()
