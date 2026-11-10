#!/usr/bin/env python3
"""Cross-preset SOUND FONT GENERATOR sweep for genuine ORIGINAL Creative Win95.

Generate TWO controlled groups of new presets 100..127 in exactly the already
Creative-accepted, publicly licensed SoundFont Spec Test v3.0 source bank.
Its six original presets, all instrument/sample/mod tables and PCM remain
byte-identical; only new preset headers/bags/gens are appended. Never publish
an owner's bank or any original Creative ROM/Windows driver material.

The original 28 MIDI notes must be PLAYED by real SBAWE.VXD Win95 before any
claim of parity. The generator is not an audio/hardware oracle.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

# In original Win95 CI, --historic-tools points to exact pinned Creative
# accepted P210 reference source code, NOT a guessed reimplementation.
VOL_VALUES=(0,1,10,64,127,250,500,750,959,960,961,999,1000,1440)
HOLD_VALUES=(-12000,-6000,-3600,-2400,-1200,-600,-120,-1,0,1,100,300,600,1200)
PROGRAMS=tuple(range(100,128))
SOURCE_BLOB="4768c4a0215abf49c7a2bb51ada5ba3494faa1c5"
SCHEMA="125A-original-Creative-source-derived-vol-sustain-mod-hold-sweep-1"

def require(predicate, why):
    if not predicate: raise ValueError("CREATIVE GENERATOR SWEEP REJECTED: "+why)

def sha256(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def check_plan():
    require(len(VOL_VALUES)==len(HOLD_VALUES)==14,"not balanced 14+14 input cases")
    require(len(PROGRAMS)==28 and len(set(PROGRAMS))==28,"28 unique programs")
    require(960 in VOL_VALUES and 0 in HOLD_VALUES,"P007 measured anchors absent")
    require(all(0<=x<=1440 for x in VOL_VALUES),"SF2 volume sustain domain")
    require(all(-12000<=x<=1200 for x in HOLD_VALUES),"SF2 hold timecents domain")

def derive_sweep(raw:bytes, old):
    check_plan()
    require(blob_sha(raw)==SOURCE_BLOB,"wrong original Creative-accepted public source")
    from p210_clone_verified_sf2 import (
      derive,split_riff,section_maps,get_entries,read_bag,read_gen,chunk,
      original_target_inst
    )
    from p83_generic_sf2 import inspect_sf2
    # P210 creates original-source-derived appended program zones, preserving
    # original 25 instruments and sample43 one-voice note59 reference.
    variants=tuple((0,500) for _ in VOL_VALUES)+tuple((h,500) for h in HOLD_VALUES)
    bank,cases,target=derive(raw,variants=variants,new_programs=PROGRAMS,
                            label_prefix="125A-CREATIVE")
    require(target["hold_tc"]==0 and target["sustain"]==500,
            "source instrument changed before construction")
    top,fields=split_riff(bank)
    tab=section_maps(fields)
    ins=get_entries(tab[b"inst"],22)
    ibag=get_entries(tab[b"ibag"],4)
    igen=get_entries(tab[b"igen"],4)
    idx=target["instrument"]
    start=struct.unpack_from("<H",ins[idx],20)[0]
    stop=struct.unpack_from("<H",ins[idx+1],20)[0]
    inherited={}
    note59=[]
    for bag in range(start,stop):
        gi=read_bag(ibag[bag])[0]
        gz=read_bag(ibag[bag+1])[0]
        current={op:(v-65536 if v>=32768 else v)
                 for op,v in map(read_gen,igen[gi:gz])}
        if 53 not in current: inherited.update(current); continue
        active={**inherited,**current}
        a,b=(0,127)
        if 43 in active:
            rg=active[43]&65535;a=rg&255;b=rg>>8
        if active.get(53)==43 and a<=59<=b: note59.append(active)
    require(len(note59)==1,"not exactly one source authenticated sample43 zone")
    instrument_vol=note59[0].get(37,0)
    # Actual source's original generator #37 could be absent/nonzero.
    require(-1440<=instrument_vol<=1440,
            "unexpected original source instrument SustainVolEnv baseline")
    require(all(-32768<=v-instrument_vol<=32767 for v in VOL_VALUES),
            "preset additive generator outside signed16")
    new_phdr=get_entries(tab[b"phdr"],38)
    new_pbag=get_entries(tab[b"pbag"],4)
    old_pgen=get_entries(tab[b"pgen"],4)
    new_pgen=list(old_pgen)
    manifest=[]
    for i,program in enumerate(PROGRAMS):
        indexes=[j for j,h in enumerate(new_phdr[:-1])
                 if struct.unpack_from("<HH",h,20)==(program,0)]
        require(len(indexes)==1,"appended program missing")
        pr=indexes[0]
        a=struct.unpack_from("<H",new_phdr[pr],24)[0]
        z=struct.unpack_from("<H",new_phdr[pr+1],24)[0]
        require(z-a==2,"P210 appended preset has unexpected bag layout")
        targets=[]
        for bag in range(a,z):
            gi=read_bag(new_pbag[bag])[0];gz=read_bag(new_pbag[bag+1])[0]
            for k in range(gi,gz):
                op,oldval=read_gen(old_pgen[k])
                if op==29:targets.append(k)
        require(len(targets)==1,"not exactly one new preset EG1 mod sustain")
        target_index=targets[0]
        if i<len(VOL_VALUES):
            value=VOL_VALUES[i]
            new_pgen[target_index]=struct.pack("<Hh",37,value-instrument_vol)
            mode="volume-sustain"
            expected=value
        else:
            value=HOLD_VALUES[i-len(VOL_VALUES)]
            # Keep this program's original ModSustain=500 and vary only
            # the original program's HoldModEnv via P210's additive op27.
            mode="modulation-hold"
            expected=value
        manifest.append({"program":program,"mode":mode,"generator_value":value,
                         "expected_merged_value":expected,"note":59,"velocity":100,
                         "sample_id":43,"source_instrument_id":idx,
                         "source_volume_sustain_cB":instrument_vol})
    replacement={b"pgen":b"".join(new_pgen)}
    pdta=b"pdta"+b"".join(chunk(tag,replacement.get(tag,data))
                         for tag,data,_ in fields)
    rebuilt=b"sfbk"+b"".join(chunk(tag,pdta if tag==b"LIST" and data[:4]==b"pdta" else data)
                              for tag,data,_ in top)
    final=b"RIFF"+struct.pack("<I",len(rebuilt))+rebuilt
    source_inspect=inspect_sf2(raw); outcome=inspect_sf2(final)
    require(outcome["preset_count"]==34 and outcome["instrument_count"]==25 and
            outcome["sample_count"]==44 and
            outcome["sample_pcm_bytes"]==source_inspect["sample_pcm_bytes"],
            "original sample inventory modified or 28 programs missing")
    _,newfields=split_riff(final);nt=section_maps(newfields)
    _,sourcefields=split_riff(raw);st=section_maps(sourcefields)
    for p in (b"inst",b"ibag",b"igen",b"imod",b"shdr",b"pmod"):
        require(nt[p]==st[p],"source instrument/sample modified "+repr(p))
    for p,width in ((b"phdr",38),(b"pbag",4),(b"pgen",4)):
        require(nt[p][:len(st[p])-width]==st[p][:-width],
                "existing public preset records altered "+repr(p))
    newtop,_=split_riff(final)
    for tag,data,_ in split_riff(raw)[0]:
        if tag==b"LIST" and data[:4]!=b"pdta":
            require(any(k==tag and d==data for k,d,_ in newtop),
                    "original source INFO/SDTA/sample PCM changed")
    require(all(m["program"]==p for m,p in zip(manifest,PROGRAMS)),
            "case identity permuted")
    return final,{"schema":SCHEMA,
        "public_accepted_source_git_blob":SOURCE_BLOB,
        "source_sha256":sha256(raw),"derived_sha256":sha256(final),
        "original_pcm_byte_identical":True,
        "original_presets_instrument_sample_tables_unchanged":True,
        "original_instrument_volume_sustain_cB":instrument_vol,
        "target_reference_source_id":idx,
        "cases":manifest,
        "original_Creative_driver_executed":False}

def self_test():
    check_plan()
    try:
        check_plan.__globals__["PROGRAMS"]=(100,)*28
        check_plan()
    except ValueError:
        pass
    else:raise AssertionError("Duplicated preset program mutant was not rejected")
    finally:
        check_plan.__globals__["PROGRAMS"]=tuple(range(100,128))
    try:
        check_plan.__globals__["VOL_VALUES"]=tuple(range(14))
        check_plan()
    except ValueError:
        pass
    else:raise AssertionError("Deleted P007 sustain960 anchor was not rejected")
    finally:
        check_plan.__globals__["VOL_VALUES"]=VOL_VALUES_ORIGINAL
    check_plan()
    print("CREATIVE_ENVELOPE_SWEEP_CONTROL_AND_NEGATIVE_MUTATIONS_PASS")

VOL_VALUES_ORIGINAL=VOL_VALUES

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--source",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--manifest",type=Path)
    ap.add_argument("--historic-tools",type=Path)
    args=ap.parse_args()
    self_test()
    if args.self_test:return
    require(all((args.source,args.out,args.manifest,args.historic_tools)),
            "source, output, manifest and pinned historic tools required")
    sys.path.insert(0,str(args.historic_tools.resolve()))
    actual=args.source.read_bytes()
    bank,manifest=derive_sweep(actual,None)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    require(not args.out.exists() and not args.manifest.exists(),
            "refusing overwrite of previous test evidence")
    args.out.write_bytes(bank)
    args.manifest.write_text(json.dumps(manifest,indent=2)+"\n")
    print("ORIGINAL_CREATIVE_ACCEPTED_SF2_GENERATOR_SWEEP_PREPARED",
          manifest["derived_sha256"],
          "28_cases_NO_ORIGINAL_DRIVER_RUN_YET")
if __name__=="__main__":main()
