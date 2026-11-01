#!/usr/bin/env python3
"""P34: Reject bogus Creative note-on traces, then compare real register values.

A trace MUST come from a separately verified, genuine Creative Win95 guest,
not the unvalidated P31 DOS SF2 experiment. This tool does not provide the VM.
Requires two trace files from identical SF2, ROM, note, bank and velocity.
No third-party binary or private SoundFont is bundled.
"""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path

PORTS = {0x600:"D0",0x602:"D0H",0xA00:"D1",0xA02:"D2",0xE00:"D3"}
NAMES = {
    ("D0",0):"CPF", ("D0",1):"PTRX", ("D0",2):"CVCF",
    ("D0",3):"VTFT",("D0",6):"PSST",("D0",7):"CSL",
    ("D0H",0):"CPF^",("D0H",1):"PTRX^",("D0H",2):"CVCF^",
    ("D0H",3):"VTFT^",("D0H",6):"PSST^",("D0H",7):"CSL^",
    ("D1",0):"CCCA",("D1",4):"ENVVOL",("D1",5):"DCYSUSV",
    ("D1",6):"ENVVAL",("D1",7):"DCYSUS",
    ("D2",0):"CCCA^",("D2",4):"ATKHLDV",("D2",5):"LFO1VAL",
    ("D2",6):"ATKHLD",("D2",7):"LFO2VAL",
    ("D3",0):"IP",("D3",1):"IFATN",("D3",2):"PEFE",
    ("D3",3):"FMMOD",("D3",4):"TREMFRQ",("D3",5):"FM2FRQ2"
}
COMPARE = ("IP","IFATN","ENVVOL","ATKHLDV","DCYSUSV",
           "ENVVAL","ATKHLD","DCYSUS","LFO1VAL","LFO2VAL",
           "FMMOD","PEFE","TREMFRQ","FM2FRQ2",
           "CSL^","PTRX^","PSST^","CCCA^")
DRAM_BASE = 0x200000

def parse(trace: str):
    pointer=0
    live=collections.defaultdict(bool)
    pending=collections.defaultdict(dict)
    notes=[]
    for number,line in enumerate(trace.splitlines(),1):
        parts=line.strip().split()
        if len(parts)<3 or parts[0].startswith("#") or parts[0]=="R":
            continue
        try:
            frame=int(parts[0])
            port=int(parts[1],16)
            value=int(parts[2],16)
        except ValueError as e:
            raise ValueError(f"bad trace row {number}: {line!r}") from e
        sel=port & 0xF02
        if sel==0xE02:
            pointer=value
            continue
        portname=PORTS.get(sel)
        if not portname:
            continue
        reg=(pointer>>5)&7
        voice=pointer & 31
        if portname in ("D1","D2") and reg==1:
            continue
        name=NAMES.get((portname,reg))
        if name is None:
            continue
        pending[voice][name]=value
        if name=="DCYSUSV":
            on=not bool(value & 0x80)
            if on and not live[voice]:
                regs=dict(pending[voice])
                if ((regs.get("CCCA",0) or (regs.get("CCCA^",0)&0xFF))
                        and regs.get("ATKHLDV",0)):
                    addr=(regs.get("CCCA",0) |
                          ((regs.get("CCCA^",0)&0xFF)<<16))
                    notes.append({"frame":frame,"voice":voice,
                                  "start_address":addr,"registers":regs})
                pending[voice]={}
            live[voice]=on
    return notes

def validate(notes, expected):
    reasons=[]
    if len(notes)!=expected:
        reasons.append(f"expected {expected} note layers, found {len(notes)}")
    for i,n in enumerate(notes):
        if not DRAM_BASE <= n["start_address"] < 0x1000000:
            reasons.append(f"voice {i} starts outside SF2 sample RAM: "
                           f"0x{n['start_address']:06X}")
        missing={"IP","IFATN","ENVVOL","ATKHLDV","DCYSUSV","CCCA"}-n["registers"].keys()
        if missing:
            reasons.append(f"voice {i}: missing {', '.join(sorted(missing))}")
    return reasons

def compare(a,b):
    # Pair by IP first, not by voice allocation index; the Win95 VXD assigns
    # voices in jumps of three, while other driver families may differ.
    a=sorted(a,key=lambda n:(n["registers"].get("IP",-1),n["start_address"]))
    b=sorted(b,key=lambda n:(n["registers"].get("IP",-1),n["start_address"]))
    out=[]
    for index,(ours,original) in enumerate(zip(a,b)):
        diff={}
        for key in COMPARE:
            av=ours["registers"].get(key)
            bv=original["registers"].get(key)
            if av is not None and bv is not None and av != bv:
                diff[key]={"125a":av,"original_win95":bv}
        # Different RAM reserve/address allocation may change low sample
        # address. Report, do not blindly label a driver conversion error.
        out.append({"layer_index":index,"ip_125a":ours["registers"].get("IP"),
                    "ip_original":original["registers"].get("IP"),
                    "start_address_125a":ours["start_address"],
                    "start_address_original":original["start_address"],
                    "register_differences":diff})
    return out

def synthetic_trace(voices, in_ram):
    rows=[]
    for i in range(voices):
        address=(0x230000+i*100) if in_ram else (0x17000+i*100)
        # Format exactly as Core.OpenTrace outputs ISA ports.
        for port,value in (
            (0xE22,(0<<5)|i),(0xA20,address&0xFFFF),
            (0xA22,(address>>16)&255),
            (0xE22,(0<<5)|i),(0xE20,0xE100+i),
            (0xE22,(1<<5)|i),(0xE20,0xFF10),
            (0xE22,(4<<5)|i),(0xA22,0x7F00),
            (0xA20,0x8000),
            (0xE22,(5<<5)|i),(0xA20,0x7F00),
        ):
            rows.append(f"0 {port:03X} {value:04X}")
    return "\n".join(rows)+"\n"

def selftest():
    good=parse(synthetic_trace(2,True))
    assert len(good)==2, f"parser generated {len(good)} instead of 2"
    assert not validate(good,2), validate(good,2)
    assert not any(x["register_differences"] for x in compare(good,good))
    assert validate(parse(synthetic_trace(16,False)),2)
    assert validate(parse(synthetic_trace(4,True)),2)
    print("PASS P34 synthetic trace parser, valid 2-layer, rejected 16 ROM voices")
    print("NOT RUN: original Win95 guest or genuine SF2 parity")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ours",type=Path)
    ap.add_argument("--original-win95",type=Path)
    ap.add_argument("--program",type=int,choices=(0,7))
    ap.add_argument("--out",default="P34-noteon-validation.json")
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        selftest()
        return
    if args.ours is None or args.original_win95 is None or args.program is None:
        ap.error("--ours --original-win95 and --program are required")
    expected=2 if args.program==0 else 4
    ours=parse(args.ours.read_text(encoding="utf8"))
    theirs=parse(args.original_win95.read_text(encoding="utf8"))
    gate_ours=validate(ours,expected)
    gate_original=validate(theirs,expected)
    report={
       "program":args.program,"expected_layers":expected,
       "ours_found":len(ours),"original_win95_found":len(theirs),
       "gate":("PASS" if not gate_ours and not gate_original else "FAIL"),
       "125a_errors":gate_ours,"original_errors":gate_original,
       "paired_registers":compare(ours,theirs) if not gate_ours and not gate_original else [],
       "originality_assertion":"Input guest provenance must be verified independently",
       "sound_fidelity_claim":False}
    Path(args.out).write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print(json.dumps(report,indent=2))
    if report["gate"]!="PASS":
        raise SystemExit(2)

if __name__=="__main__":
    main()
