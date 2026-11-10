#!/usr/bin/env python3
"""Original-source-derived, genuine Creative Win95 28 crossed SF2 VOL sustain cases.

Vary SustainVolEnv (generator #37) on an INSTRUMENT and as an independent
additive PRESET delta. This tests actual two-stage vs merged translation on
original Creative SBAWE.VXD, not just 14 preset-only conversion anchors.

Starts with public, previously accepted SoundFont Spec Test v3.0 (pinned Git
blob), never publishes the author's or user's original SoundFont bytes.
Original six presets, 25 original instruments, 44 samples and complete PCM
must remain unchanged. 4 new clones of original one-voice instrument sample43
and 28 appended preset zones are the ONLY changes. No synthesized oracle.
"""
from __future__ import annotations
import argparse,hashlib,json,struct,sys
from pathlib import Path

BASES=(0,250,500,1000)
TARGETS=(0,1,249,250,500,750,1000)
PROGRAMS=tuple(range(100,128))
CASES=tuple((pr,base,target)
            for pr,(base,target) in zip(PROGRAMS,
                ((b,t) for b in BASES for t in TARGETS)))
SOURCE_BLOB="4768c4a0215abf49c7a2bb51ada5ba3494faa1c5"
SCHEMA="125A-original-Creative-vol-sustain-instrument-preset-crossed-28-v1"

def require(ok,reason):
    if not ok:raise ValueError("CREATIVE VOLUME TWO-STAGE REJECTED: "+reason)

def u16(x):return x&0xffff

def signed(v):return v-65536 if v>=32768 else v

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def source_zone_volume(tab,instrument_id, note=59):
    from p210_clone_verified_sf2 import get_entries,read_bag,read_gen
    ins=get_entries(tab[b"inst"],22)
    ibag=get_entries(tab[b"ibag"],4)
    igen=get_entries(tab[b"igen"],4)
    start=struct.unpack_from("<H",ins[instrument_id],20)[0]
    end=struct.unpack_from("<H",ins[instrument_id+1],20)[0]
    global_gen={}
    out=[]
    for bag in range(start,end):
        gi=read_bag(ibag[bag])[0]
        gz=read_bag(ibag[bag+1])[0]
        here={op:signed(val) for op,val in map(read_gen,igen[gi:gz])}
        if 53 not in here:global_gen.update(here);continue
        merged={**global_gen,**here}
        rg=u16(merged.get(43,0x7f00))
        low,high=rg&255,(rg>>8)&255
        if merged.get(53)==43 and low<=note<=high:
            out.append(merged.get(37,0))
    require(len(out)==1,
        f"source instrument {instrument_id} must have exactly one sample43 note59 region")
    return out[0]

def make(raw):
    from p83_generic_sf2 import inspect_sf2
    from p210_clone_verified_sf2 import (
        derive,split_riff,section_maps,get_entries,read_bag,read_gen,chunk,
    )
    require(len(CASES)==28 and len(set(CASES))==28,"broken 4x7 matrix")
    require(git_blob(raw)==SOURCE_BLOB,"wrong Creative-accepted public SF2 source")
    original_inventory=inspect_sf2(raw)
    require((original_inventory["preset_count"],original_inventory["instrument_count"],
             original_inventory["sample_count"])==(6,25,44),
            "original SoundFont inventory is not the P210 Creative reference")
    # P210's append-only proven variant shape has global preset Hold0 and
    # no change to original sample voices. Keep ModSustain 500 invariant.
    variants=tuple((0,500) for _ in CASES)
    intermediate,_,target=derive(
        raw,variants=variants,new_programs=PROGRAMS,label_prefix="VOL")
    original_id=target["instrument"]
    require(target["sustain"]==500 and target["hold_tc"]==0,
            "reference source note59 is not the original accepted P210 region")
    top,fields=split_riff(intermediate)
    tab=section_maps(fields)
    source_tab=section_maps(split_riff(raw)[1])

    inst=get_entries(tab[b"inst"],22)
    ibag=get_entries(tab[b"ibag"],4)
    igen=get_entries(tab[b"igen"],4)
    imod=get_entries(tab[b"imod"],10)
    phdr=get_entries(tab[b"phdr"],38)
    pbag=get_entries(tab[b"pbag"],4)
    pgen=get_entries(tab[b"pgen"],4)
    baseline=source_zone_volume(tab,original_id)
    require(-1440<=baseline<=1440,"original test source has unexpected volume generator")

    start=struct.unpack_from("<H",inst[original_id],20)[0]
    end=struct.unpack_from("<H",inst[original_id+1],20)[0]
    require(start<end<len(ibag),"source original instrument bag bounds")
    new_inst=list(inst[:-1]); new_bags=list(ibag[:-1])
    new_gen=list(igen[:-1]);new_mod=list(imod[:-1])
    ids={}
    for base in BASES:
        iid=len(new_inst)
        ids[base]=iid
        label=f"CREA-VOL-{base:04d}".encode("ascii").ljust(20,b"\0")
        require(len(label)==20,"instrument name field overflow")
        new_inst.append(label+struct.pack("<H",len(new_bags)))
        changed=0
        for bag in range(start,end):
            ia,ma=read_bag(ibag[bag])
            iz,mz=read_bag(ibag[bag+1])
            require(ia<=iz and ma<=mz,"invalid original zone")
            here=[read_gen(x) for x in igen[ia:iz]]
            sample_zone=any(op==53 for op,val in here)
            new_bags.append(struct.pack("<HH",len(new_gen),len(new_mod)))
            had=False
            for op,val in here:
                if op==37 and sample_zone:
                    val=u16(base);had=True;changed+=1
                if op==53 and sample_zone and not had:
                    new_gen.append(struct.pack("<HH",37,u16(base)))
                    had=True;changed+=1
                new_gen.append(struct.pack("<HH",op,val))
            new_mod.extend(imod[ma:mz])
        require(changed>0,"no SustainVolEnv inserted in cloned instrument local sample zones")
    final_inst=bytearray(inst[-1])
    struct.pack_into("<H",final_inst,20,len(new_bags))
    new_inst.append(bytes(final_inst))
    new_bags.append(struct.pack("<HH",len(new_gen),len(new_mod)))
    new_gen.append(igen[-1]);new_mod.append(imod[-1])
    # Modify each newly appended P210 preset only; 27=Hold0, 41=new cloned
    # instrument ID and preset op29→37 with additive target-base.
    new_pgen=list(pgen)
    meta=[]
    for program,base,total in CASES:
        indexes=[i for i,h in enumerate(phdr[:-1])
                 if struct.unpack_from("<HH",h,20)==(program,0)]
        require(len(indexes)==1,"appended program not unique")
        pr=indexes[0]
        a=struct.unpack_from("<H",phdr[pr],24)[0]
        z=struct.unpack_from("<H",phdr[pr+1],24)[0]
        changed={29:0,41:0}
        for bag in range(a,z):
            first=read_bag(pbag[bag])[0]
            last=read_bag(pbag[bag+1])[0]
            for i in range(first,last):
                op,val=read_gen(pgen[i])
                if op==29:
                    new_pgen[i]=struct.pack("<HH",37,u16(total-base))
                    changed[29]+=1
                elif op==41:
                    new_pgen[i]=struct.pack("<HH",41,ids[base])
                    changed[41]+=1
        require(changed=={29:1,41:1},"incorrect preset generator mutation")
        meta.append({"program":program,"instrument_sustain_base":base,
            "preset_sustain_delta":total-base,
            "requested_total_volume_sustain":total,
            "volume_sustain_generator_id":37,"note":59,"velocity":100,
            "original_sample_id":43,"original_instrument":original_id,
            "cloned_instrument":ids[base]})
    replacements={b"inst":b"".join(new_inst),b"ibag":b"".join(new_bags),
        b"igen":b"".join(new_gen),b"imod":b"".join(new_mod),
        b"pgen":b"".join(new_pgen)}
    updated_pdta=b"pdta"+b"".join(
        chunk(tag,replacements.get(tag,data)) for tag,data,_ in fields)
    body=b"sfbk"+b"".join(
        chunk(tag,updated_pdta if tag==b"LIST" and data[:4]==b"pdta" else data)
        for tag,data,_ in top)
    result=b"RIFF"+struct.pack("<I",len(body))+body
    inv=inspect_sf2(result)
    require((inv["preset_count"],inv["instrument_count"],inv["sample_count"])==
            (34,29,44),"mutated bank has incorrect preset/instrument/sample count")
    require(inv["sample_pcm_bytes"]==original_inventory["sample_pcm_bytes"],
            "original audio PCM size changed")
    t2=section_maps(split_riff(result)[1])
    for op,width in ((b"inst",22),(b"ibag",4),(b"igen",4),(b"imod",10)):
        require(t2[op][:len(source_tab[op])-width]==source_tab[op][:-width],
                "original instrument generators/metadata changed "+repr(op))
    for op in (b"phdr",b"pbag",b"pmod",b"shdr"):
        if op==b"phdr":
            require(t2[op][:len(source_tab[op])-38]==source_tab[op][:-38],
                    "original six presets changed")
        elif op==b"pbag":
            require(t2[op][:len(source_tab[op])-4]==source_tab[op][:-4],
                    "original preset bags changed")
        else:require(t2[op]==source_tab[op],"original SF2 metadata changed "+repr(op))
    require(t2[b"pgen"][:len(source_tab[b"pgen"])-4]==source_tab[b"pgen"][:-4],
            "original preset generator rows mutated")
    for tag,data,_ in split_riff(raw)[0]:
        if tag==b"LIST" and data[:4]!=b"pdta":
            require(any(k==tag and d==data for k,d,_ in split_riff(result)[0]),
                    "original public SF2 samples/INFO changed")
    for base,iid in ids.items():
        require(source_zone_volume(t2,iid)==base,
                "cloned instrument actual SustainVolEnv does not match base")
    require(len(meta)==28 and all(m["instrument_sustain_base"]+
            m["preset_sustain_delta"]==m["requested_total_volume_sustain"]
            for m in meta),"generator deltas or case provenance not valid")
    manifest={
        "schema":SCHEMA,"public_source_git_blob":SOURCE_BLOB,
        "original_audio_pcm_byte_identical":True,
        "original_six_presets_preserved":True,
        "original_25_instruments_preserved":True,
        "original_44_sample_records_preserved":True,
        "original_instrument_37_baseline":baseline,
        "original_note59_instrument":original_id,
        "source_sha256":hashlib.sha256(raw).hexdigest(),
        "derived_sf2_sha256":hashlib.sha256(result).hexdigest(),
        "instrument_bases":list(BASES),"target_values":list(TARGETS),
        "cases":meta,"real_original_driver_executed":False,
        "proprietary_user_media_included":False}
    return result,manifest

def self_test():
    assert len(CASES)==28 and [p for p,_,_ in CASES]==list(PROGRAMS)
    assert len({(b,t) for _,b,t in CASES})==28
    assert all(-1000<=t-b<=1000 for _,b,t in CASES)
    # Mutate a single case to ensure 4x7 checker refuses false controls.
    require(sum(b==500 for _,b,_ in CASES)==7,"source crossed controls missing")
    for seq in (CASES[:-1],(CASES[0],)+CASES[1:-1],CASES[::-1]):
        try:
            require(len(seq)==28 and list(seq)==list(CASES) and
                    len(set(seq))==28,"bad mutated program matrix")
        except ValueError:pass
        else:raise AssertionError("mutant matrix incorrectly accepted")
    print("CREATIVE_VOLUME_SUSTAIN_28_CROSSED_CONTROLS_PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--historic-tools",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    self_test()
    if a.self_test:return
    require(a.source and a.out and a.manifest and a.historic_tools,
            "source, out, manifest and vetted P210 scripts required")
    sys.path.insert(0,str(a.historic_tools.resolve()))
    raw=a.source.read_bytes()
    final,metadata=make(raw)
    require(not a.out.exists() and not a.manifest.exists(),
            "do not overwrite original evidence")
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.manifest.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_bytes(final)
    a.manifest.write_text(json.dumps(metadata,indent=2)+"\n")
    print("CREATIVE_VOLUME_SUSTAIN_28_PUBLIC_SOURCE_DERIVED",
          metadata["derived_sf2_sha256"],"Original Win95 NOT YET RUN")
if __name__=="__main__":main()
