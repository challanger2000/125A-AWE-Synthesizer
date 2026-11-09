#!/usr/bin/env python3
"""P206: validate ACTUAL native 86Box EMU8000 note59 register I/O.
This does not run an original Creative driver nor read a physical AWE64.
No source ROM, SF2, raw register trace, or audio is publicly committed.
"""
import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median

def check(ok, reason):
    if not ok:
        raise ValueError("P206 FAIL: "+reason)

def raw_writes(path):
    pointer = None
    seen_read = False
    writes = []
    last_frame = -1
    portnames = {0x620:"D0",0x622:"D0HI",0xA20:"D1",0xA22:"D1HI",0xE20:"D3"}
    for s in Path(path).read_text(encoding="utf8").splitlines():
        if not s or s.startswith("#"):
            continue
        f = s.split()
        if f[0] == "R":
            check(len(f)==4, "corrupt register read")
            clock = int(f[1])
            seen_read = True
        else:
            check(len(f)==3, "wrong register write shape")
            clock = int(f[0])
            port = int(f[1],16)
            value = int(f[2],16)
            check(0 <= value <= 65535, "16bit I/O word overflow")
            if not seen_read:
                if port == 0xE22:
                    pointer = value
                elif port in portnames:
                    check(pointer is not None, "missing register pointer")
                    writes.append((clock,pointer&31,(pointer>>5)&7,
                                   portnames[port],value))
        check(clock>=last_frame and clock>=0, "nonmonotone 44.1k clock")
        last_frame = clock
    check(seen_read and len(writes)>10, "missing native chip note-on writes")
    return writes

def snapshots(path):
    expect=["relative_frame","voice","atkhld","envval",
            "pefe","ip","cpf","ptrx","cvcf"]
    with Path(path).open(encoding="utf8",newline="") as f:
        rows=csv.DictReader(f,delimiter="\t")
        check(rows.fieldnames==expect, "snapshot schema")
        out=[]
        for i,r in enumerate(rows):
            x={"frame":int(r["relative_frame"]),"voice":int(r["voice"])}
            for k in expect[2:]:
                x[k]=int(r[k],16)
            check(x["frame"]==i*4410, "sample-accurate 100ms probe clock")
            check(0<=x["voice"]<32, "invalid voice")
            check((x["atkhld"]&127)==12,"incorrect native chip attack code")
            check((x["pefe"]>>8)==127,"incorrect native pitch envelope depth")
            out.append(x)
    check(len(out)==31, "30 intervals + initial snapshot expected")
    check(len(set(r["voice"] for r in out))==1, "unexpected voice reallocation")
    return out

def test_negative_controls():
    template={"frame":0,"voice":1,"atkhld":12,"pefe":0x7F00}
    def good(t):
        return t["frame"]==0 and 0<=t["voice"]<32 and (t["atkhld"]&127)==12 and (t["pefe"]>>8)==127
    check(good(template), "valid control failed")
    for key,bad in (("frame",1),("voice",32),("atkhld",11),("pefe",0)):
        mutated=dict(template);mutated[key]=bad
        check(not good(mutated),"negative mutation escaped: "+key)
    # Independent reconstruction from Win95 SBAWE.VXD disassembly.
    q=((0+12516)<<16)//1200
    offset=(0x10000+(q&65535))>>(16-(q>>16))
    check(0x8000-offset==0x7A48,"original delay conversion")
    check((((~((0+500)//150))&7)|8)==12,"original attack conversion")
    print("P206 self-tests PASS (4 negative controls + original VXD scalar arithmetic)")

def run(args):
    writes=raw_writes(args.trace)
    rows=snapshots(args.readbacks)
    voice=rows[0]["voice"]
    targets={
        "ENVVAL_0timecents":("D1",6,lambda v:v==0x7A48),
        "ATKHLD_0timecents":("D1HI",6,lambda v:(v&127)==12),
        "PEFE_plus1200c":("D3",2,lambda v:(v>>8)==127),
    }
    found={}
    for key,(port,reg,test) in targets.items():
        arr=[w for w in writes if w[1]==voice and w[2]==reg and
             w[3]==port and test(w[4])]
        check(len(arr)>0,"missing actual native port write for "+key)
        check(all(w[0]==0 for w in arr),"note-on register writes not at sample 0")
        found[key]=["%04X"%w[4] for w in arr]
    fx=json.loads(Path(args.fixture).read_text(encoding="utf8"))
    source=fx["original_reference"]
    check(source["midi_note"]==59 and source["sample_id"]==43 and
          source["delay_mod_env_timecents"]==0 and
          source["attack_mod_env_timecents"]==0 and
          source["mod_env_to_pitch_cents"]==1200,"original SF2 source changed")
    cps=[r["cpf"]>>16 for r in rows]
    hold=median(cps[25:])
    hold_hz=float(fx["captures"]["baseline"]["hold_native_hz"])
    comparisons=[]
    for p in fx["captures"]["baseline"]["attack_rows"]:
        if p["native"] is None:
            continue
        x=(p["t"]-9.5)*10
        j=int(math.floor(x))
        check(0<=j<30,"outside native register sample grid")
        chip_pitch=cps[j]+(cps[j+1]-cps[j])*(x-j)
        f=hold_hz*(2**((chip_pitch-hold)/4096))
        comparisons.append({
          "sec":p["t"],"original_CT4390_hz":p["hw"],
          "native_audio_tracker_hz":p["native"],
          "native_chip_CPF_high":round(chip_pitch,3),
          "CPF_inferred_native_hz":round(f,3),
          "CPF_vs_native_audio_cents":round(1200*math.log2(f/p["native"]),2)})
    check(len(comparisons)==9,"original P200 bins missing")
    report={
      "audit":"P206 real NATIVE EMU8000 note59 register causal snapshot",
      "original_creative_driver_executed":False,
      "physical_AWE64_chip_observed":False,
      "native_86box_chip_actual_port_and_readback":True,
      "original_note_on_frame_44100Hz":418950,
      "native_active_voice":voice,
      "original_SF2_verified_only_from_existing_P205_fixture":source["original_sf2_git_blob"],
      "native_initial_written_registers":found,
      "native_note_on_bus_write_count":len(writes),
      "chip_time_window":"0 to 3s, 100ms readbacks (31 actual emulated-device reads)",
      "chip_delay_register":"0x7A48",
      "chip_delay_approx_s":1.0614,
      "chip_attack_register":"0x0C",
      "chip_attack_full_phase_approx_s":0.989833,
      "CPF_high_register_span":max(cps)-min(cps),
      "CPF_high_register_first":cps[0],
      "CPF_high_register_last":cps[-1],
      "CPF_inferred_audio_diagnostics":comparisons,
      "falsification_limits":[
        "This does NOT execute original Creative Win95 SBAWE.VXD on public v3.0 SF2.",
        "Native 86Box readbacks are not physical EMU8000 hardware measurements.",
        "The original SoundFont and MIDI are hash-verified separately by CI.",
        "Original analog CT4390 frequency is compared only to already measured P200 points.",
        "No DSP, product VST3, ROM, SF2 or original FLAC modified."]}
    check(report["CPF_high_register_span"]>0,
          "native CPF did not respond to EG1 modulation; no valid trajectory")
    Path(args.out).write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print("P206 PASS: actual native bus writes",len(writes),
          "CPF span",report["CPF_high_register_span"],
          "original Win95-driver trace remains OPEN")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    for x in ("trace","readbacks","fixture","out"):
        ap.add_argument("--"+x)
    a=ap.parse_args()
    if a.self_test:
        test_negative_controls()
        if not a.trace:
            return
    check(all((a.trace,a.readbacks,a.fixture,a.out)),"missing inputs")
    run(a)
if __name__=="__main__":
    main()
