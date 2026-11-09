#!/usr/bin/env python3
"""P210: Create a derived, ephemeral 14-case EG1 research bank by preserving
the EXACT audio/INFO/SDTA/sample headers of the already Creative-Win95-accepted
public SoundFont Spec Test v3.0. Do not publish generated SoundFont bytes.

The earlier fully synthetic 10KiB SF2 passed standard parser QA, but did NOT
load in the genuine Creative Win95 guest: no DRAM upload and no EMU8000 note I/O.
This variant keeps the accepted source's six presets and 25 instruments, then
adds 14 instruments by copying exactly the reference sampleID43/note59 zone,
changing ONLY holdModEnv (op27) and sustainModEnv (op29).
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from p83_generic_sf2 import inspect_sf2, chunks
from p210_make_eg1_sf2 import VARIANTS, chunk, lst, name20, require

ORIGINAL_GIT_SHA = "4768c4a0215abf49c7a2bb51ada5ba3494faa1c5"
ORIGINAL_PRESETS = 6
ORIGINAL_INSTRUMENTS = 25
ORIGINAL_SAMPLES = 44

def parse(raw):
    require(raw[:4]==b"RIFF" and raw[8:12]==b"sfbk", "source not SF2")
    root=[]
    for ident,payload in chunks(raw,12,len(raw)):
        root.append((ident,bytes(payload)))
    return root

def derive(raw):
    meta=inspect_sf2(raw)
    require((meta["preset_count"],meta["instrument_count"],meta["sample_count"])
            ==(6,25,44),"unexpected known-good public reference structure")
    top=parse(raw)
    pdta={}
    for tag,payload in top:
        if tag==b"LIST" and payload[:4]==b"pdta":
            for sub,body in chunks(payload,4,len(payload)):
                pdta[sub]=bytes(body)
    required=(b"phdr",b"pbag",b"pgen",b"inst",b"ibag",b"igen",b"shdr")
    require(all(n in pdta for n in required),"reference pdta incomplete")
    phdr,pbag,pgen,inst,ibag,igen=[pdta[n] for n in required[:-1]]
    require((len(phdr)//38-1,len(inst)//22-1)==(6,25),
            "unexpected reference preset/instrument table counts")
    require(len(pbag)%4==0 and len(pgen)%4==0 and len(ibag)%4==0
            and len(igen)%4==0,"unexpected record alignment")
    oldPbag=len(pbag)//4-1
    oldPgen=len(pgen)//4-1
    oldIbag=len(ibag)//4-1
    oldIgen=len(igen)//4-1
    require((oldPbag,oldPgen,oldIbag,oldIgen)==(33,34,145,580),
            "source metadata counts shifted unexpectedly")
    # Exact known-good original note59 instrument is "vol-envelope" (#10).
    start,=struct.unpack_from("<H",inst,10*22+20)
    stop,=struct.unpack_from("<H",inst,11*22+20)
    source_zone=None
    for bag in range(start,stop):
        g0,=struct.unpack_from("<H",ibag,bag*4)
        g1,=struct.unpack_from("<H",ibag,(bag+1)*4)
        gs=[struct.unpack_from("<HH",igen,4*g) for g in range(g0,g1)]
        opmap={op:val for op,val in gs}
        if opmap.get(53)==43 and opmap.get(43)==(59|(59<<8)):
            require(source_zone is None,"ambiguous original note59 sample")
            source_zone=gs
    require(source_zone is not None,"original note59 zone not found")
    expected={7:1200,25:0,26:0,27:0,28:0,29:500,30:0,53:43}
    require(all(dict(source_zone).get(k)==v for k,v in expected.items()),
            "original note59 EG1 source differs from P197")
    require(source_zone[-1]==(53,43),"SF2 sampleID must remain last")

    # Keep all known-good instrument/gen/header/sample bytes and append cases.
    new_phdr=bytearray(phdr[:-38])
    new_pbag=bytearray(pbag[:-4])
    new_pgen=bytearray(pgen[:-4])
    new_inst=bytearray(inst[:-22])
    new_ibag=bytearray(ibag[:-4])
    new_igen=bytearray(igen[:-4])
    report=[]
    num_gens=len(source_zone)
    for i,(tc,per) in enumerate(VARIANTS):
        program=6+i
        instrument=25+i
        new_phdr+=name20("P210 EG1 %02d"%i)
        new_phdr+=struct.pack("<HHHIII",program,0,oldPbag+i,0,0,0)
        new_pbag+=struct.pack("<HH",oldPgen+i,0)
        new_pgen+=struct.pack("<HH",41,instrument)
        new_inst+=name20("P210 ENV %02d"%i)
        new_inst+=struct.pack("<H",oldIbag+i)
        new_ibag+=struct.pack("<HH",oldIgen+i*num_gens,0)
        adjusted=[(op,(tc&65535) if op==27 else per if op==29 else val)
                  for op,val in source_zone]
        require(adjusted[-1]==(53,43) and [x[0] for x in adjusted]==
                [x[0] for x in source_zone],"source zone structure modified")
        for op,val in adjusted:
            new_igen+=struct.pack("<HH",op,val)
        report.append({"program":program,"note":59,"hold_mod_env_tc":tc,
                      "sustain_mod_env_permille":per,"original_sample_id":43,
                      "original_instrument_zone":10,
                      "original_sample_bytes_preserved":True})
    n=len(VARIANTS)
    new_phdr+=name20("EOP")+struct.pack("<HHHIII",0,0,oldPbag+n,0,0,0)
    new_pbag+=struct.pack("<HH",oldPgen+n,0)
    new_pgen+=struct.pack("<HH",0,0)
    new_inst+=name20("EOI")+struct.pack("<H",oldIbag+n)
    new_ibag+=struct.pack("<HH",oldIgen+n*num_gens,0)
    new_igen+=struct.pack("<HH",0,0)
    replacements={
        b"phdr":bytes(new_phdr),b"pbag":bytes(new_pbag),
        b"pgen":bytes(new_pgen),b"inst":bytes(new_inst),
        b"ibag":bytes(new_ibag),b"igen":bytes(new_igen)
    }
    rebuilt=[]
    for tag,payload in top:
        if tag==b"LIST" and payload[:4]==b"pdta":
            children=[]
            for sub,body in chunks(payload,4,len(payload)):
                children.append(chunk(sub,replacements.get(sub,bytes(body))))
            rebuilt.append(lst(b"pdta",*children))
        else:
            rebuilt.append(chunk(tag,payload))
    body=b"sfbk"+b"".join(rebuilt)
    derived=b"RIFF"+struct.pack("<I",len(body))+body
    checked=inspect_sf2(derived)
    require((checked["preset_count"],checked["instrument_count"],
             checked["sample_count"])==(20,39,44),
            "derived bank structure invalid")
    require([x["program"] for x in checked["presets"]][-14:]==list(range(6,20)),
            "generated 14 programs not indexed as expected")
    verify=parse(derived)
    for original,present in zip(top,verify):
        if original[0]==b"LIST" and original[1][:4]==b"pdta":
            continue
        require(original==present,"original INFO/SDTA/source samples changed")
    return derived,report

def self_test(path):
    raw=Path(path).read_bytes()
    derived,cases=derive(raw)
    require(derived==derive(raw)[0],"nondeterministic carrier transformation")
    require(len(cases)==14 and len(set((x["hold_mod_env_tc"],
                                        x["sustain_mod_env_permille"])
                                       for x in cases))==14,
            "14 dimensional cases not preserved")
    # Check that only the intentionally changed two zone generators vary.
    require(cases[4]["hold_mod_env_tc"]==0 and
            cases[4]["sustain_mod_env_permille"]==500,
            "baseline original-note case missing")
    print("P210 reference carrier PASS: 6 verified original presets + 14 copies of actual original note59 zone")
    return derived,cases

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reference",type=Path,required=True)
    p.add_argument("--sf2",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    raw,cases=self_test(a.reference)
    if a.self_test and not a.sf2:return
    require(a.sf2 and a.manifest,"output SoundFont and derived metadata required")
    a.sf2.parent.mkdir(parents=True,exist_ok=True)
    a.manifest.parent.mkdir(parents=True,exist_ok=True)
    a.sf2.write_bytes(raw)
    a.manifest.write_text(json.dumps({
      "schema":"P210-generated-EG1-v1",
      "synthetic_only":False,
      "source_original_reference_copied_ephemerally":True,
      "source_git_blob":ORIGINAL_GIT_SHA,
      "source_sample_bytes_preserved":True,
      "sf2_sha256":hashlib.sha256(raw).hexdigest(),
      "programs":cases,
      "note":"Only derived numeric manifest can be uploaded. Preserve original reference/ROM/SF2 as transient runner files."
    },indent=2)+"\n")
    print("P210 derived research SF2",len(raw),"bytes; SHA256",
          hashlib.sha256(raw).hexdigest())
if __name__=="__main__":main()
