#!/usr/bin/env python3
"""P87: losslessly reduce any private SF2 to requested audition programs/notes.

Samples are COPIED word-for-word from the original (not synthesized, converted,
interpolated or normalized). Preset/instrument generator/modulator zones are
preserved; all indices and 16-bit PCM offsets are remapped into an independent
valid RIFF SoundFont. The result is only a test fixture for the selected notes,
not a replacement for the complete original SoundFont.
DO NOT COMMIT ANY GENERATED USER SOUND FONT TO THE PUBLIC REPOSITORY.
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path

def chunk(tag,data):
    return tag+struct.pack("<I",len(data))+data+(b"\0" if len(data)&1 else b"")

def walk(data,begin,end):
    pos=begin
    while pos+8<=end:
        tag=bytes(data[pos:pos+4])
        size,=struct.unpack_from("<I",data,pos+4)
        finish=pos+8+size
        if finish>end:raise ValueError("Truncated SF2 chunk "+str(tag))
        yield tag,bytes(data[pos+8:finish])
        pos=finish+(size&1)
    if pos!=end:raise ValueError("Misaligned SF2 chunk")

def listchunk(tag,subchunks):
    return chunk(b"LIST",tag+b"".join(subchunks))

def u16(data,offset):
    return struct.unpack_from("<H",data,offset)[0]

def zone(gens,mods,bags,index):
    g0,m0=struct.unpack_from("<HH",bags,index*4)
    g1,m1=struct.unpack_from("<HH",bags,(index+1)*4)
    return ([(u16(gens,j*4),u16(gens,j*4+2)) for j in range(g0,g1)],
            [mods[j*10:(j+1)*10] for j in range(m0,m1)])

def reassemble_zones(grouped,remap):
    bags=bytearray();gens=bytearray();mods=bytearray()
    for groups in grouped:
        for operators,modulators in groups:
            bags+=struct.pack("<HH",len(gens)//4,len(mods)//10)
            for op,value in operators:
                if op in remap:value=remap[op][value]
                gens+=struct.pack("<HH",op,value)
            mods+=b"".join(modulators)
    bags+=struct.pack("<HH",len(gens)//4,len(mods)//10)
    return bytes(bags),bytes(gens+b"\0"*4),bytes(mods+b"\0"*10)

def subset(raw,programs=(0,17),notes=(36,38,42),bank=0):
    if raw[:4]!=b"RIFF" or raw[8:12]!=b"sfbk":
        raise ValueError("Expected SF2 RIFF")
    sections={}
    for tag,body in walk(raw,12,len(raw)):
        if tag==b"LIST":
            for sub,data in walk(body,4,len(body)):
                sections[(body[:4],sub)]=data
    required=(b"phdr",b"pbag",b"pmod",b"pgen",b"inst",b"ibag",b"imod",b"igen",b"shdr")
    pdta={key:sections[(b"pdta",key)] for key in required}
    phdr,pbag,pmod,pgen,inst,ibag,imod,igen,shdr=(pdta[k] for k in required)
    pcm=sections[(b"sdta",b"smpl")]
    selected_presets=[];instrument_ids=set()
    for program in programs:
        matching=[i for i in range(len(phdr)//38-1)
                  if u16(phdr,i*38+20)==program and u16(phdr,i*38+22)==bank]
        if len(matching)!=1:raise ValueError("Missing or ambiguous SF2 program "+str(program))
        index=matching[0]
        start=u16(phdr,index*38+24);end=u16(phdr,(index+1)*38+24)
        groups=[zone(pgen,pmod,pbag,i) for i in range(start,end)]
        instrument_ids.update(value for gens,mods in groups for op,value in gens if op==41)
        selected_presets.append((phdr[index*38:(index+1)*38],groups))
    selected_instruments=[];sample_ids=set()
    for index in sorted(instrument_ids):
        if index>=len(inst)//22-1:raise ValueError("Instrument index out of bounds")
        start=u16(inst,index*22+20);end=u16(inst,(index+1)*22+20)
        groups=[]
        for i in range(start,end):
            operators,modulators=zone(igen,imod,ibag,i)
            value=next((v for op,v in operators if op==43),0x7f00)
            low,high=value&255,value>>8
            sample=next((v for op,v in operators if op==53),None)
            if sample is None or any(low<=n<=high for n in notes):
                groups.append((operators,modulators))
                if sample is not None:sample_ids.add(sample)
        selected_instruments.append((index,inst[index*22:(index+1)*22],groups))
    if not sample_ids:raise ValueError("No matching source sample zones")
    inst_indices={old:new for new,(old,_,_) in enumerate(selected_instruments)}
    sample_indices={old:new for new,old in enumerate(sorted(sample_ids))}
    smpl=bytearray();headers=[]
    for old in sorted(sample_ids):
        if old>=len(shdr)//46-1:raise ValueError("Sample index out of bounds")
        record=bytearray(shdr[old*46:(old+1)*46])
        start,end,loop_start,loop_end=struct.unpack_from("<IIII",record,20)
        if not (0<=start<=loop_start<=loop_end<=end<=len(pcm)//2):
            raise ValueError("Invalid sample/loop bounds")
        # Preserve 46 SF2 interpolation guard words, where present.
        copy_to=min(end+46,len(pcm)//2)
        new_start=len(smpl)//2
        smpl+=pcm[2*start:2*copy_to]
        struct.pack_into("<IIII",record,20,new_start,new_start+end-start,
                         new_start+loop_start-start,new_start+loop_end-start)
        headers.append(bytes(record))
    p_bag,p_gen,p_mod=reassemble_zones([x[1] for x in selected_presets],{41:inst_indices})
    i_bag,i_gen,i_mod=reassemble_zones([x[2] for x in selected_instruments],{53:sample_indices})
    new_phdr=bytearray();index=0
    for old,groups in selected_presets:
        record=bytearray(old);struct.pack_into("<H",record,24,index)
        new_phdr+=record;index+=len(groups)
    terminal=bytearray(phdr[-38:]);struct.pack_into("<H",terminal,24,index)
    new_phdr+=terminal
    new_inst=bytearray();index=0
    for _,old,groups in selected_instruments:
        record=bytearray(old);struct.pack_into("<H",record,20,index)
        new_inst+=record;index+=len(groups)
    terminal=bytearray(inst[-22:]);struct.pack_into("<H",terminal,20,index)
    new_inst+=terminal
    eos=bytearray(shdr[-46:]);total=len(smpl)//2
    struct.pack_into("<IIII",eos,20,total,total,total,total)
    info=listchunk(b"INFO",[chunk(k,v) for (typ,k),v in sections.items() if typ==b"INFO"])
    sdta=listchunk(b"sdta",[chunk(b"smpl",bytes(smpl))])
    pdta=listchunk(b"pdta",[chunk(k,v) for k,v in (
        (b"phdr",bytes(new_phdr)),(b"pbag",p_bag),(b"pmod",p_mod),(b"pgen",p_gen),
        (b"inst",bytes(new_inst)),(b"ibag",i_bag),(b"imod",i_mod),(b"igen",i_gen),
        (b"shdr",b"".join(headers)+bytes(eos)))])
    body=b"sfbk"+info+sdta+pdta
    return b"RIFF"+struct.pack("<I",len(body))+body

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--programs",default="0,17")
    p.add_argument("--notes",default="36,38,42")
    p.add_argument("--bank",default=0,type=int)
    a=p.parse_args()
    numbers=lambda s:[int(v) for v in s.split(",")]
    output=subset(a.original.read_bytes(),numbers(a.programs),numbers(a.notes),a.bank)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_bytes(output)
    print("P87 private exact PCM SF2 subset:",len(output),"bytes")

if __name__=="__main__":
    main()
