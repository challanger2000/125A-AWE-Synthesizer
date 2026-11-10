#!/usr/bin/env python3
"""P214: vary ORIGINAL INSTRUMENT sustain and PRESET sustain independently.

Preserve the historically Creative-accepted SoundFont's six presets, all
original 25 instruments, 44 original samples and all unchanged source bytes
outside appended SF2 instrument/preset tables. Clone only the source
instrument whose note59 sample43 region was independently authenticated in
P210/P212. Test Creative Windows 95 against 28 crossed (base, target) values.

Research-only. Synthetic/minimal SF2 without Creative provenance not accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from p83_generic_sf2 import inspect_sf2
from p210_clone_verified_sf2 import (
    SOURCE_GIT_BLOB, NOTE, chunk, derive, get_entries, original_target_inst,
    read_bag, read_gen, section_maps, split_riff,
)

BASES=(0,250,500,1000)
TARGETS=(0,1,249,250,500,750,1000)
PROGRAMS=tuple(range(100,128))
CASES=tuple((program,base,sustain)
            for program,(base,sustain) in zip(
                PROGRAMS,((b,s) for b in BASES for s in TARGETS)))
SCHEMA="P214-original-Creative-multi-instrument-sustain-v1"


def require(ok,reason):
    if not ok:raise ValueError("P214 SOURCE-AUTHENTIC INSTRUMENT MATRIX: "+reason)


def signed(x):
    return x-65536 if x>=32768 else x


def require_matrix(matrix=CASES):
    require(len(matrix)==28 and
            [c[0] for c in matrix]==list(PROGRAMS),"28 exact distinct programs")
    require(set((b,s) for _,b,s in matrix)==set((b,s) for b in BASES for s in TARGETS),
            "incomplete or duplicated crossed 4x7 instrument/preset experiment")
    require(all(type(b) is int and type(s) is int and
                0<=b<=1000 and 0<=s<=1000 and -1000<=s-b<=1000
                for _,b,s in matrix),"out-of-domain SF2 layer delta")
    require(sum(b!=500 for _,b,_ in matrix)==21 and
            sum(b==500 for _,b,_ in matrix)==7,"21 new-base plus seven replay controls")


def instrument_sustain_for_note(tab,iid):
    ins=get_entries(tab[b"inst"],22)
    ibag=get_entries(tab[b"ibag"],4)
    igen=get_entries(tab[b"igen"],4)
    require(0<=iid<len(ins)-1,"instrument ID")
    start=struct.unpack_from("<H",ins[iid],20)[0]
    stop=struct.unpack_from("<H",ins[iid+1],20)[0]
    global_ops={}
    hits=[]
    for bag in range(start,stop):
        ia=read_bag(ibag[bag])[0]
        iz=read_bag(ibag[bag+1])[0]
        ops={op:val for op,val in map(read_gen,igen[ia:iz])}
        if 53 not in ops:
            global_ops.update(ops)
        else:
            combined={**global_ops,**ops}
            keylo,keyhi=(0,127)
            if 43 in combined:keylo,keyhi=combined[43]&255,combined[43]>>8
            if combined[53]==43 and keylo<=NOTE<=keyhi:
                require(29 in combined,"source sample43 mod sustain generator absent")
                hits.append(signed(combined[29]))
    require(len(hits)==1,"not one original sample43 note59 zone on new instrument")
    return hits[0]


def derive_matrix(source):
    require_matrix()
    original_source_git_blob=hashlib.sha1(
        b"blob "+str(len(source)).encode("ascii")+b"\0"+source).hexdigest()
    require(original_source_git_blob==SOURCE_GIT_BLOB,
            "not identical Creative-accepted public SoundFont v3.0 source")
    source_report=inspect_sf2(source)
    require(source_report["preset_count"]==6 and
            source_report["instrument_count"]==25 and
            source_report["sample_count"]==44,"source SoundFont inventory changed")

    # P210's original-source-preserving preset extension has been proven to
    # load with the original Win95 Creative driver. Extend it without changing
    # any existing original instrument or 44-Sample PCM data.
    variants=tuple((0,s) for _,_b,s in CASES)
    preliminary,_,original_target=derive(
        source,variants=variants,new_programs=PROGRAMS,label_prefix="P214")
    _,orig_fields=split_riff(preliminary)
    tab=section_maps(orig_fields)
    original_iid=original_target["instrument"]
    require(original_target["sustain"]==500 and
            instrument_sustain_for_note(tab,original_iid)==500,
            "original public instrument reference not Sustain 500")

    inst=get_entries(tab[b"inst"],22)
    ibag=get_entries(tab[b"ibag"],4)
    igen=get_entries(tab[b"igen"],4)
    imod=get_entries(tab[b"imod"],10)
    phdr=get_entries(tab[b"phdr"],38)
    pbag=get_entries(tab[b"pbag"],4)
    pgen=get_entries(tab[b"pgen"],4)

    original_inst_bag_a=struct.unpack_from("<H",inst[original_iid],20)[0]
    original_inst_bag_z=struct.unpack_from("<H",inst[original_iid+1],20)[0]
    require(0<=original_inst_bag_a<original_inst_bag_z<len(ibag),
            "source instrument zone boundaries wrong")
    new_inst=inst[:-1]
    new_ibag=ibag[:-1]
    new_igen=igen[:-1]
    new_imod=imod[:-1]
    clone_ids={500:original_iid}
    modified_sustain_records={}
    for base in BASES:
        if base==500:continue
        iid=len(new_inst)
        clone_ids[base]=iid
        name=f"P214 BASE {base:04d}".encode("ascii").ljust(20,b"\0")
        new_inst.append(name+struct.pack("<H",len(new_ibag)))
        modified=0
        for bag in range(original_inst_bag_a,original_inst_bag_z):
            ia,ma=read_bag(ibag[bag])
            iz,mz=read_bag(ibag[bag+1])
            require(ia<=iz and ma<=mz,"invalid original instrument bag ordering")
            new_ibag.append(struct.pack("<HH",len(new_igen),len(new_imod)))
            for record in igen[ia:iz]:
                op,value=read_gen(record)
                if op==29 and signed(value)==500:
                    record=struct.pack("<HH",29,base)
                    modified+=1
                new_igen.append(record)
            new_imod.extend(imod[ma:mz])
        require(modified>=1,"cloned instrument lacks originally declared Sustain 500")
        modified_sustain_records[str(base)]=modified
    end_inst=bytearray(inst[-1])
    struct.pack_into("<H",end_inst,20,len(new_ibag))
    new_inst.append(bytes(end_inst))
    new_ibag.append(struct.pack("<HH",len(new_igen),len(new_imod)))
    new_igen.append(igen[-1])
    new_imod.append(imod[-1])

    # Modify ONLY appended 28 preset generators: choose a cloned original
    # instrument, and encode actual additive generator delta (target-base).
    new_pgen=list(pgen)
    metadata=[]
    for program,base,sustain in CASES:
        indexes=[i for i,h in enumerate(phdr[:-1])
                 if struct.unpack_from("<HH",h,20)==(program,0)]
        require(len(indexes)==1,"source-derived new preset program missing")
        idx=indexes[0]
        a=struct.unpack_from("<H",phdr[idx],24)[0]
        z=struct.unpack_from("<H",phdr[idx+1],24)[0]
        counts={29:0,41:0}
        for bag in range(a,z):
            gi=read_bag(pbag[bag])[0]
            gz=read_bag(pbag[bag+1])[0]
            for k in range(gi,gz):
                op,_=read_gen(pgen[k])
                if op==29:
                    new_pgen[k]=struct.pack("<HH",29,(sustain-base)&0xffff)
                    counts[29]+=1
                elif op==41:
                    new_pgen[k]=struct.pack("<HH",41,clone_ids[base])
                    counts[41]+=1
        require(counts=={29:1,41:1},"unexpected new preset generator layout")
        metadata.append({
          "program":program,"base_instrument_sustain":base,
          "sustain_mod_env_permille":sustain,"preset_sustain_delta":sustain-base,
          "instrument_id":clone_ids[base],"source_original_instrument_id":original_iid,
          "note":59,"sample_id":43,"velocity":100,
          "hold_mod_env_tc":0,
          "generator_semantics":"original sample43 cloned instrument generator + additive preset generator"})
    overrides={b"inst":b"".join(new_inst),
               b"ibag":b"".join(new_ibag),
               b"igen":b"".join(new_igen),
               b"imod":b"".join(new_imod),
               b"pgen":b"".join(new_pgen)}
    top,_=split_riff(preliminary)
    pdta=b"pdta"+b"".join(chunk(name,overrides.get(name,data))
                         for name,data,_ in orig_fields)
    body=b"sfbk"+b"".join(
       chunk(tag,pdta if tag==b"LIST" and data[:4]==b"pdta" else data)
       for tag,data,_ in top)
    result=b"RIFF"+struct.pack("<I",len(body))+body
    inventory=inspect_sf2(result)
    require(inventory["preset_count"]==34 and
            inventory["instrument_count"]==28 and
            inventory["sample_count"]==44 and
            inventory["sample_pcm_bytes"]==source_report["sample_pcm_bytes"] and
            inventory["sample_memory_fits"],"modified derived bank inventory invalid")
    new_top,new_fields=split_riff(result)
    newtab=section_maps(new_fields)
    # Independent structural equality: source PCM, original six programs,
    # original 25 instrument headers and all original instrument zone records.
    require(newtab[b"inst"][:len(tab[b"inst"])-22]==
            tab[b"inst"][:-22],"original instrument headers changed")
    for t in (b"ibag",b"igen",b"imod"):
        width={b"ibag":4,b"igen":4,b"imod":10}[t]
        require(newtab[t][:len(tab[t])-width]==tab[t][:-width],
                "original instrument generator/modulator records changed: "+repr(t))
    for t in (b"phdr",b"pbag",b"pmod",b"shdr"):
        require(newtab[t]==tab[t],"original preset/sample table changed: "+repr(t))
    require(newtab[b"pgen"][:len(section_maps(split_riff(source)[1])[b"pgen"])-4]==
            section_maps(split_riff(source)[1])[b"pgen"][:-4],
            "original six preset generators changed")
    for tag,data,_ in top:
        if tag==b"LIST" and data[:4]!=b"pdta":
            require(any(n==tag and d==data for n,d,_ in new_top),
                    "source INFO/SDTA audio or metadata changed")
    for base,iid in clone_ids.items():
        require(instrument_sustain_for_note(newtab,iid)==base,
                "cloned instrument does not have requested sample43 note59 sustain")
    require(len(metadata)==28 and all(m["preset_sustain_delta"]+
            m["base_instrument_sustain"]==m["sustain_mod_env_permille"]
            for m in metadata),"preset/zone generator values unverified")
    return result,metadata,clone_ids,modified_sustain_records


def selftest():
    require_matrix()
    for bad in (CASES[:-1],CASES[:-1]+(CASES[0],),
                tuple(reversed(CASES)),
                tuple((pr,b,1001 if pr==100 else s) for pr,b,s in CASES)):
        try:require_matrix(bad)
        except ValueError:pass
        else:raise AssertionError("P214 corrupt crossed fixture plan accepted")
    print("P214 fixture-only sanity PASS: four instrument bases, seven outcomes each; 21 genuinely new-base cases")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    selftest()
    if args.self_test and not args.source:return
    require(args.source and args.out and args.manifest,
            "real source, derived bank and manifest paths required")
    source=args.source.read_bytes()
    bank,metadata,ids,modified=derive_matrix(source)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(bank)
    manifest={
      "schema":SCHEMA,"origin":"unchanged authenticated public source; appended 3 cloned instrument layers and 28 controlled presets",
      "public_original_source_git_blob":SOURCE_GIT_BLOB,
      "source_sha256":hashlib.sha256(source).hexdigest(),
      "sf2_sha256":hashlib.sha256(bank).hexdigest(),
      "original_six_presets_preserved":True,
      "original_25_instruments_preserved":True,
      "original_44_sample_records_preserved":True,
      "original_audio_pcm_byte_identical":True,
      "instrument_bases":list(BASES),"requested_sustain_values":list(TARGETS),
      "original_instrument_clones":ids,
      "new_instrument_sustain_records_changed":modified,
      "cases":metadata,"original_media_published":False,
      "physical_hardware_present":False,
      "real_original_Creative_win95_test":"NOT RUN - set only in independent guest verifier",
    }
    args.manifest.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    print("P214 original-audio-source-preserving derived matrix:",len(metadata),
          "presets, 3 cloned instrument variants, 21 new-base cases; SHA256",manifest["sf2_sha256"])
if __name__=="__main__":main()
