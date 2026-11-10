#!/usr/bin/env python3
"""P217: independently test original Creative Win95 SF2 filter register mappings.

Create 28 append-only source-authenticated presets: 7 each Cutoff, Q,
modulation envelope depth and modulation LFO depth. An original accepted
SoundFont's 25 instruments, 44 samples, six presets and audio are preserved.
No expected Creative register outputs are calculated or authored here.
"""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from p83_generic_sf2 import inspect_sf2
from p210_clone_verified_sf2 import (
 SOURCE_GIT_BLOB, NOTE, chunk, derive, get_entries, original_target_inst,
 read_bag, read_gen, section_maps, split_riff,
)
OPS=((8,"initialFilterFc", (1500,3500,5500,7500,9500,11500,13500),13500),
     (9,"initialFilterQ", (0,10,30,60,100,240,960),0),
     (11,"modEnvToFilterFc",(-12000,-6000,-1200,0,1200,6000,12000),0),
     (10,"modLfoToFilterFc",(-12000,-6000,-1200,0,1200,6000,12000),0))
CASES=tuple((100+i*7+j,op,label,value,default)
            for i,(op,label,vals,default) in enumerate(OPS)
            for j,value in enumerate(vals))
SCHEMA="P217-original-Creative-filter-28-source-preserved-v1"
def require(condition,reason):
    if not condition:raise ValueError("P217 filter fixture INVALID: "+reason)
def signed(n):return n-65536 if n>=32768 else n

def instrument_values(tab,iid):
    inst=get_entries(tab[b"inst"],22);bags=get_entries(tab[b"ibag"],4)
    gen=get_entries(tab[b"igen"],4)
    require(iid>=0 and iid+1<len(inst),"invalid original instrument id")
    start=struct.unpack_from("<H",inst[iid],20)[0]
    stop=struct.unpack_from("<H",inst[iid+1],20)[0]
    inherited={};hits=[]
    for i in range(start,stop):
        left=read_bag(bags[i])[0];right=read_bag(bags[i+1])[0]
        ops={op:signed(val) for op,val in map(read_gen,gen[left:right])}
        if 53 not in ops:
            inherited.update(ops);continue
        combined={**inherited,**ops}
        low,high=0,127
        if 43 in combined:
            low=combined[43]&255;high=(combined[43]>>8)&255
        if combined[53]==43 and low<=NOTE<=high:hits.append(combined)
    require(len(hits)==1,"not one original sample43 note59 zone")
    return hits[0]

def selftest():
    require(len(CASES)==28 and [c[0] for c in CASES]==list(range(100,128)),
            "program indexes not 28 unique 100..127")
    require(set(c[1] for c in CASES)=={8,9,10,11},"missing filter generator")
    require(all(len(set(c[3] for c in CASES if c[1]==op))==7 for op in (8,9,10,11)),
            "seven distinct values per filter dimension")
    require(all(-32768<=c[3]<=32767 for c in CASES),"value out of SF2 i16")
    assert 0 in [c[3] for c in CASES if c[1]==9]
    for damaged in (CASES[:-1],CASES[:15]+(CASES[14],)+CASES[16:],
                    tuple(reversed(CASES))):
        try:
            require(len(damaged)==28 and
                [c[0] for c in damaged]==list(range(100,128)) and
                len({(c[1],c[3]) for c in damaged})==28,
                "destroyed matrix")
        except ValueError:continue
        raise AssertionError("P217 erroneous matrix accepted")
    print("P217 filter matrix selftest PASS 28 programs, four independent dimensions, three negative mutations")

def make(source):
    selftest()
    blob=hashlib.sha1(b"blob "+str(len(source)).encode()+b"\0"+source).hexdigest()
    require(blob==SOURCE_GIT_BLOB,"not exactly Creative-accepted source SF2")
    source_info=inspect_sf2(source)
    require(source_info["preset_count"]==6 and source_info["instrument_count"]==25
        and source_info["sample_count"]==44,"source bank inventory mismatch")
    variants=tuple((0,500) for _ in CASES)
    preliminary,_,instrument=derive(source,variants=variants,
        new_programs=tuple(c[0] for c in CASES),label_prefix="P217")
    top,fields=split_riff(preliminary)
    original_top,original_fields=split_riff(source)
    orig=section_maps(original_fields)
    tab=section_maps(fields)
    iid=instrument["instrument"]
    actual=instrument_values(tab,iid)
    bases={op:actual.get(op,dflt) for op,_,_,dflt in OPS}
    require(all(-32768<=base<=32767 for base in bases.values()),"invalid instrument base")
    # We alter only appended PGEN: each has exactly a hold-offset record
    # op27, a sustain-offset record op29 and an instrument selector op41.
    # Replace its op27 record with the independently requested filter op.
    phdr=get_entries(tab[b"phdr"],38)
    pbag=get_entries(tab[b"pbag"],4)
    pgen=get_entries(tab[b"pgen"],4)
    newgen=list(pgen)
    metadata=[]
    for program,op,label,target,_ in CASES:
        positions=[i for i,p in enumerate(phdr[:-1])
          if struct.unpack_from("<HH",p,20)==(program,0)]
        require(len(positions)==1,f"appended program {program} not unique")
        pi=positions[0]
        a=struct.unpack_from("<H",phdr[pi],24)[0]
        z=struct.unpack_from("<H",phdr[pi+1],24)[0]
        seen={27:0,29:0,41:0}
        for i in range(a,z):
            left=read_bag(pbag[i])[0];right=read_bag(pbag[i+1])[0]
            for j in range(left,right):
                gen,val=read_gen(pgen[j])
                require(gen in seen,"unexpected appended generator op "+str(gen))
                seen[gen]+=1
                if gen==27:
                    delta=target-bases[op]
                    require(-32768<=delta<=32767,"unrepresentable signed SF2 preset generator delta")
                    newgen[j]=struct.pack("<Hh",op,delta)
                elif gen==29:require(val==0,"original sustain offset must remain zero")
                elif gen==41:require(val==iid,"source instrument selector changed")
        require(seen=={27:1,29:1,41:1},"incorrect appended preset op count")
        metadata.append({"program":program,"generator_operator":op,
            "generator_name":label,"instrument_base_value":bases[op],
            "requested_effective_value":target,
            "preset_additive_offset":target-bases[op],
            "original_instrument_id":iid,
            "reference_sample_id":43,"midi_note":59,"velocity":100,
            "other_three_filter_parameters_not_modified":True,
            "no_original_Creative_register_values_embedded":True})
    newgen_blob=b"".join(newgen)
    require(newgen_blob[:len(orig[b"pgen"])-4]==orig[b"pgen"][:-4],
        "original six preset generators must stay byte identical")
    new_pdta=b"pdta"+b"".join(chunk(k,newgen_blob if k==b"pgen" else d)
                           for k,d,_ in fields)
    body=b"sfbk"+b"".join(chunk(t,new_pdta if t==b"LIST" and d[:4]==b"pdta" else d)
                       for t,d,_ in top)
    bank=b"RIFF"+struct.pack("<I",len(body))+body
    inv=inspect_sf2(bank)
    require(inv["preset_count"]==34 and inv["instrument_count"]==25 and
      inv["sample_count"]==44 and inv["sample_pcm_bytes"]==source_info["sample_pcm_bytes"]
      and inv["sample_memory_fits"],"derived bank invalid")
    newtop,newfields=split_riff(bank);newtab=section_maps(newfields)
    for name in (b"inst",b"ibag",b"igen",b"imod",b"pmod",b"shdr"):
        require(newtab[name]==orig[name],"original instrument/modulator/sample tables changed "+str(name))
    for name in (b"phdr",b"pbag"):
        width=38 if name==b"phdr" else 4
        require(newtab[name][:len(orig[name])-width]==orig[name][:-width],
                "original six preset bag/header changed "+str(name))
    for t,d,_ in original_top:
        if t==b"LIST" and d[:4]!=b"pdta":
            require(any(x==t and y==d for x,y,_ in newtop),
                    "source audio/INFO changed from original")
    return bank,metadata,bases

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    selftest()
    if args.self_test and not args.source:return
    require(all((args.source,args.out,args.manifest)),"source, derived bank and output manifest required")
    source=args.source.read_bytes()
    bank,metadata,bases=make(source)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(bank)
    obj={"schema":SCHEMA,"public_original_source_git_blob":SOURCE_GIT_BLOB,
         "source_sha256":hashlib.sha256(source).hexdigest(),
         "derived_sf2_sha256":hashlib.sha256(bank).hexdigest(),
         "original_6_presets_preserved":True,"original_25_instruments_preserved":True,
         "original_44_sample_records_preserved":True,"original_audio_bytes_identical":True,
         "original_instrument_filter_bases":{str(k):v for k,v in bases.items()},
         "matrix":metadata,"independent_original_Creative_driver_data":"NOT YET COLLECTED",
         "P216_product_DSP_modified":False,"original_sample_media_published":False}
    args.manifest.write_text(json.dumps(obj,indent=2)+"\n",encoding="utf8")
    print("P217 derived genuine source SoundFont: 28 filter cases, four controls, 44 original samples, sha256",obj["derived_sf2_sha256"])
if __name__=="__main__":main()
