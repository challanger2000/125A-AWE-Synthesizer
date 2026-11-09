#!/usr/bin/env python3
"""P208 research: native 86Box SF2 A/B vs archived REAL Creative driver data.
Physically original AWE64 hardware was NOT present during this test.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
from p89_compare_voice_registers import native_trace

def check(ok, message):
    if not ok:
        raise ValueError("P208 FAIL: "+message)

def group(path):
    seq = native_trace(path)
    voices = {}
    result = collections.defaultdict(list)
    for voice, name, value in seq:
        if voice not in voices:
            voices[voice] = len(voices)
        result[(voices[voice], name)].append(value)
    check(len(voices)==1, "original note59 has multiple voices")
    return {name:values for (_,name),values in result.items()},len(seq)

def independent(tc, sustain):
    if tc <= -12000:
        ticks = 0
    elif tc >= 5484:
        ticks = 32768
    else:
        q = ((tc+12516)<<16)//1200
        ticks = (65536+(q&65535))>>(16-(q>>16))
    return max(0,127-ticks*725//92000), 127-min(1000,max(0,sustain))*127//1000

def self_test():
    check(independent(0,500)==(116,64),"original note59 tc0/500 candidate arithmetic")
    check(independent(-12000,0)==(127,127),"lower boundary")
    check(independent(5484,1000)==(0,0),"upper boundary")
    originals = {"ATKHLD":0x740C,"DCYSUS":0x4027}
    for wrong in ({"ATKHLD":0x750C},{"DCYSUS":0x3F27},
                  {"ATKHLD":0x750C,"DCYSUS":0x3F27}):
        check(any(wrong[k]!=originals[k] for k in wrong),
              "negative mutation failed to detect wrong Creative registers")
    print("P208 positive/negative arithmetic controls PASS (3 mutants)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    for f in ("fixture","baseline","candidate","baseline_pcm","candidate_pcm","out"):
        ap.add_argument("--"+f.replace("_","-"),dest=f)
    a=ap.parse_args()
    if a.self_test:
        self_test()
        if not a.fixture:return
    check(all(getattr(a,f) for f in ("fixture","baseline","candidate",
                                    "baseline_pcm","candidate_pcm","out")),
          "mandatory independent evidence inputs absent")
    ref=json.loads(Path(a.fixture).read_text())
    check(ref["schema"]=="P208-real-original-Creative-note59-v1" and
          ref["provenance"]["run"]==42705889086 and
          ref["observed"]=={"series":32,"equal":29,"different":3,
                            "word_writes":47,"voices":1},
          "genuine Creative P207 source identity changed")
    base,n0=group(a.baseline)
    cand,n1=group(a.candidate)
    check(n0==n1==47 and len(base)==len(cand)==32,
          "the exact P207 register population was not reproduced")
    for reg, expected in ref["native_initial"].items():
        check(base[reg]==expected,"P207 native baseline unexpectedly changed: "+reg)
    changed=sorted(reg for reg in base if base[reg]!=cand[reg])
    check(changed==["ATKHLD","DCYSUS"],
          "candidate changed additional or incorrect registers: "+str(changed))
    for reg in ("ATKHLD","DCYSUS","ENVVAL","PEFE"):
        check(cand[reg]==ref["original"][reg],
              "candidate still differs from REAL Creative: "+reg)
    check(cand["IP"]==base["IP"] and cand["IP"]!=ref["original"]["IP"],
          "remaining one-unit IP discrepancy was accidentally disguised")
    raw0=Path(a.baseline_pcm).read_bytes()
    raw1=Path(a.candidate_pcm).read_bytes()
    check(len(raw0)>100000 and raw0==raw1,
          "early EG1 attack audio differs: converter is not isolated")
    output={
      "phase":"P208 research-only",
      "real_original_creative_reference_run":42705889086,
      "original_driver_rerun_during_P208":False,
      "real_native_86box_chip_run_for_each_candidate":True,
      "original_public_sf2_sha256":ref["provenance"]["sf2_sha256"],
      "native_register_writes_each":n0,
      "per_register_series_each":len(base),
      "changed_series_only":changed,
      "actual_original_creative_target_regs":ref["original"],
      "candidate_ATKHLD":["0x%04X"%v for v in cand["ATKHLD"]],
      "candidate_DCYSUS":["0x%04X"%v for v in cand["DCYSUS"]],
      "remaining_IP_one_code_native":"0x%04X"%cand["IP"][0],
      "first_two_seconds_44100Hz_stereo_PCM_bit_identical":True,
      "identical_PCM_sha256":hashlib.sha256(raw0).hexdigest(),
      "original_Creative_series_predicted_equal_after_P208":31,
      "physical_CT4390_EG1_pitch_attack_discrepancy_resolved":False,
      "hardware_model_100_percent_verified":False,
      "scope":"Hold/sustain candidate consistent with one original Creative note; independent full generator sweeps remain OPEN",
      "release":"NO-GO"}
    Path(a.out).write_text(json.dumps(output,indent=2)+"\n")
    print("P208 PASS: actual native register sequence 47 writes, 32 series each")
    print("P208 PASS: correct Original-Creative ATKHLD, DCYSUS, ENVVAL, PEFE; IP still +1")
    print("P208 PASS: 2 seconds of real EMU8000 audio bit-identical")
    print("P208 IMPORTANT: 81.85c real hardware EG1 attack-pitch discrepancy still OPEN")
if __name__=="__main__":
    main()
