#!/usr/bin/env python3
"""P210 v2: append fourteen controlled EG1 presets to the ALREADY accepted
public original SoundFont Spec Test v3.0, preserving all its actual samples,
instruments, original presets, effects and non-preset generator tables.

This avoids the observed original-Creative refusal to upload a scratch-built
10 KiB minimal SoundFont. Source file must match P207 authenticated Git blob.
Only legal SF2 preset pdta phdr/pbag/pgen indices are appended; no sample data
or original zones are changed or redistributed in the evidence artifact.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
from p83_generic_sf2 import inspect_sf2
from p210_make_eg1_sf2 import VARIANTS

SOURCE_GIT_BLOB="4768c4a0215abf49c7a2bb51ada5ba3494faa1c5"
NOTE=59
NEW_PROGRAMS=tuple(range(100,114))
def check(ok,msg):
    if not ok:raise ValueError("P210 VERIFIED-SOURCE-SF2 FAILED: "+msg)
def chunk(tag,data):
    check(len(tag)==4,"chunk tag")
    return tag+struct.pack("<I",len(data))+data+(b"\0" if len(data)&1 else b"")
def split_riff(raw):
    check(raw[:4]==b"RIFF" and raw[8:12]==b"sfbk"
          and struct.unpack_from("<I",raw,4)[0]==len(raw)-8,"RIFF")
    def walk(buf,start,end):
        at=start
        while at+8<=end:
            size=struct.unpack_from("<I",buf,at+4)[0]
            stop=at+8+size+(size&1)
            check(stop<=end,"truncated RIFF chunk")
            yield bytes(buf[at:at+4]),bytes(buf[at+8:at+8+size]),bytes(buf[at:stop])
            at=stop
        check(at==end,"RIFF alignment")
    top=list(walk(raw,12,len(raw)))
    pdta=[(tag,data,entry) for tag,data,entry in top
          if tag==b"LIST" and data[:4]==b"pdta"]
    check(len(pdta)==1,"exactly one pdta LIST")
    fields=list(walk(pdta[0][1],4,len(pdta[0][1])))
    return top,fields
def get_entries(data,width):
    check(len(data)%width==0,"record alignment")
    return [data[i:i+width] for i in range(0,len(data),width)]
def section_maps(fields):
    keys=[name for name,_,_ in fields]
    needed=(b"phdr",b"pbag",b"pmod",b"pgen",b"inst",b"ibag",
            b"imod",b"igen",b"shdr")
    check(len(set(keys))==len(keys) and all(k in keys for k in needed),
          "original pdta sections")
    return {k:d for k,d,_ in fields}
def read_bag(record):
    return struct.unpack("<HH",record)
def read_gen(record):
    return struct.unpack("<HH",record)
def inst_ids_from_original_program_zero(tab):
    phdr=get_entries(tab[b"phdr"],38)
    pbag=get_entries(tab[b"pbag"],4)
    pgen=get_entries(tab[b"pgen"],4)
    idx=[i for i,h in enumerate(phdr[:-1])
         if struct.unpack_from("<HH",h,20)==(0,0)]
    check(len(idx)==1,"single existing original SF2 program0")
    start=struct.unpack_from("<H",phdr[idx[0]],24)[0]
    stop=struct.unpack_from("<H",phdr[idx[0]+1],24)[0]
    result=[]
    for bag in range(start,stop):
        a=read_bag(pbag[bag])[0]
        b=read_bag(pbag[bag+1])[0]
        for g in pgen[a:b]:
            op,val=read_gen(g)
            if op==41:result.append(val)
    check(result,"source program0 contains instrument references")
    return result
def original_target_inst(tab):
    inst=get_entries(tab[b"inst"],22)
    ibag=get_entries(tab[b"ibag"],4)
    igen=get_entries(tab[b"igen"],4)
    hits=[]
    for iid in inst_ids_from_original_program_zero(tab):
        check(iid+1<len(inst),"original instrument ID out of bounds")
        start=struct.unpack_from("<H",inst[iid],20)[0]
        stop=struct.unpack_from("<H",inst[iid+1],20)[0]
        inherited={}
        for bag in range(start,stop):
            a=read_bag(ibag[bag])[0]
            b=read_bag(ibag[bag+1])[0]
            ops={op:val for op,val in map(read_gen,igen[a:b])}
            if 53 not in ops:
                inherited.update(ops)
                continue
            local={**inherited,**ops}
            keylow,keyhigh=(0,127)
            if 43 in local:
                keylow,keyhigh=local[43]&255,local[43]>>8
            if local[53]==43 and keylow<=NOTE<=keyhigh:
                signed=lambda v:v-65536 if v>=32768 else v
                hits.append({"instrument":iid,
                  "hold_tc":signed(local[27]) if 27 in local else -12000,
                  "sustain":signed(local[29]) if 29 in local else 0,
                  "pitch_mod":signed(local[7]) if 7 in local else 0,
                  "delay_tc":signed(local[25]) if 25 in local else -12000,
                  "attack_tc":signed(local[26]) if 26 in local else -12000})
    check(len(hits)==1,"not exactly one original sample43 note59 region: "+repr(hits))
    return hits[0]
def derive(source):
    top,fields=split_riff(source)
    tab=section_maps(fields)
    source_inventory=inspect_sf2(source)
    check(source_inventory["preset_count"]==6 and
          source_inventory["instrument_count"]==25 and
          source_inventory["sample_count"]==44,
          "original public SF2 inventory changed")
    target=original_target_inst(tab)
    check(target["hold_tc"]==0 and target["sustain"]==500 and
          target["pitch_mod"]==1200 and target["delay_tc"]==0 and
          target["attack_tc"]==0,
          "original source generator differs from independently measured P200 reference: "+repr(target))
    phdr=get_entries(tab[b"phdr"],38)
    pbag=get_entries(tab[b"pbag"],4)
    pgen=get_entries(tab[b"pgen"],4)
    check(phdr[-1][:3]==b"EOP" and
          len(pgen)<65535-50 and len(pbag)<65535-30,
          "original preset terminal or 16-bit SF2 index overflow")
    phdr_terminal=phdr[-1]
    pbag_terminal=pbag[-1]
    pgen_terminal=pgen[-1]
    start_bag=len(pbag)-1
    start_gen=len(pgen)-1
    last_mod=read_bag(pbag_terminal)[1]
    new_phdr=phdr[:-1]
    new_bags=pbag[:-1]
    new_gens=pgen[:-1]
    meta=[]
    for i,(hold,sustain) in enumerate(VARIANTS):
        program=NEW_PROGRAMS[i]
        label=f"P210 EG1 {program}"
        new_phdr.append(label.encode("ascii").ljust(20,b"\0")
            +struct.pack("<HHHIII",program,0,start_bag+2*i,0,0,0))
        # Same legal global+local zone layout as original public test presets.
        global_ptr=start_gen+len(new_gens)-(len(pgen)-1)
        new_bags.extend([struct.pack("<HH",global_ptr,last_mod),
                         struct.pack("<HH",global_ptr,last_mod)])
        # SF2 preset generator values ADD to the authentic instrument values.
        # The source instrument note59 uses hold=0tc, sustain=500 units.
        new_gens.extend([struct.pack("<HH",27,(hold-target["hold_tc"])&65535),
                         struct.pack("<HH",29,(sustain-target["sustain"])&65535),
                         struct.pack("<HH",41,target["instrument"])])
        meta.append({"program":program,"hold_mod_env_tc":hold,
                     "sustain_mod_env_permille":sustain,
                     "instrument_id":target["instrument"],
                     "sample_id":43,"note":59,
                     "pitch_depth_cents":1200,
                     "generator_semantics":"additive preset delta over existing original instrument"})
    last_ptr=start_gen+len(new_gens)-(len(pgen)-1)
    new_bags.append(struct.pack("<HH",last_ptr,last_mod))
    end_terminal=bytearray(phdr_terminal)
    struct.pack_into("<H",end_terminal,24,start_bag+2*len(VARIANTS))
    new_phdr.append(bytes(end_terminal))
    new_gens.append(pgen_terminal)
    overrides={b"phdr":b"".join(new_phdr),
               b"pbag":b"".join(new_bags),
               b"pgen":b"".join(new_gens)}
    rebuilt_pdta=b"pdta"+b"".join(chunk(k,overrides.get(k,data))
                                for k,data,_ in fields)
    result=b"sfbk"+b"".join(chunk(tag,rebuilt_pdta if tag==b"LIST" and data[:4]==b"pdta" else data)
                           for tag,data,_ in top)
    derived=b"RIFF"+struct.pack("<I",len(result))+result
    v=inspect_sf2(derived)
    check(v["preset_count"]==20 and v["instrument_count"]==25
          and v["sample_count"]==44 and v["sample_pcm_bytes"]==
          source_inventory["sample_pcm_bytes"],
          "source-compatible derived SoundFont inventory invalid")
    check(sorted(x["program"] for x in v["presets"] if x["program"]>=100)
          ==list(NEW_PROGRAMS),"missing controlled original-source presets")
    _,new_fields=split_riff(derived)
    newer=section_maps(new_fields)
    for name in (b"inst",b"ibag",b"igen",b"shdr",b"pmod",b"imod"):
        check(newer[name]==tab[name],"original instrument/sample/mod tables changed: "+str(name))
    for tag,data,_ in top:
        if tag==b"LIST" and data[:4]!=b"pdta":
            newtop,_=split_riff(derived)
            check(any(t==tag and d==data for t,d,_ in newtop),"source INFO/SDTA or audio modified")
    check(newer[b"pgen"][:len(tab[b"pgen"])-4]==tab[b"pgen"][:-4] and
          newer[b"pbag"][:len(tab[b"pbag"])-4]==tab[b"pbag"][:-4] and
          newer[b"phdr"][:len(tab[b"phdr"])-38]==tab[b"phdr"][:-38],
          "existing public SoundFont preset generator records were modified")
    return derived,meta,target
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    a=p.parse_args()
    original=a.source.read_bytes()
    # A canonical git-blob identity check avoids accidental rebase to a new public bank.
    gitsha=hashlib.sha1(b"blob "+str(len(original)).encode()+b"\0"+original).hexdigest()
    check(gitsha==SOURCE_GIT_BLOB,"not original pinned public SF2 v3.0")
    b,variants,target=derive(original)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_bytes(b)
    manifest={"schema":"P210-cloned-original-EG1-v2",
      "synthetic_only":False,
      "public_original_source_git_blob":SOURCE_GIT_BLOB,
      "public_original_source_sha256":hashlib.sha256(original).hexdigest(),
      "sf2_sha256":hashlib.sha256(b).hexdigest(),
      "original_instrument_metadata":target,
      "preserved_original_audio_samples":True,
      "preserved_original_6_presets":True,
      "programs":variants,
      "source":"Original public SoundFont Spec Test 2.01, appended 14 preset-only additive variations"}
    a.manifest.parent.mkdir(parents=True,exist_ok=True)
    a.manifest.write_text(json.dumps(manifest,indent=2)+"\n")
    print("P210 v2 ORIGINAL-SOURCE-DERIVED SoundFont accepted inventory",
          "20 programs, 25 original instruments, 44 original samples.")
    print("P210 v2 original sample43 instrument",target)
    print("P210 v2 source SHA256",manifest["public_original_source_sha256"])
    print("P210 v2 derived SHA256",manifest["sf2_sha256"])
if __name__=="__main__":main()
