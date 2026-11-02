#!/usr/bin/env python3
"""P80: verify the complete original Synth 512 Bank SoundFont without rendering.

Never exports sample bytes, patches or user audio. The MIDI preset number is
phdr.wPreset, NOT the on-disk preset index (this bank's phdr is reverse sorted).
The checked bank contains 77 bank-zero programs, 0..77 except 63.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

TOTAL_PRESETS=77
PROGRAMS=set(range(78))-{63}
KNOWN={0:"Grungy Ramp Bass",7:"TX81Z Lately Bass"}
RECORD_SIZE={"phdr":38,"inst":22,"shdr":46}
MIN_SF2_RAM_KIB=0

def sf2_chunks(blob, begin, end):
    pos=begin
    while pos+8<=end:
        tag=blob[pos:pos+4]
        size,=struct.unpack_from("<I",blob,pos+4)
        nxt=pos+8+size
        if nxt>end: raise ValueError("Truncated SoundFont")
        yield tag,blob[pos+8:nxt]
        pos=nxt+(size&1)
    if pos!=end:raise ValueError("Misaligned SoundFont RIFF")

def inventory(raw):
    if len(raw)<64 or raw[:4]!=b"RIFF" or raw[8:12]!=b"sfbk":
        raise ValueError("Invalid RIFF/sfbk header")
    size,=struct.unpack_from("<I",raw,4)
    if size+8!=len(raw):raise ValueError("RIFF file size mismatch")
    sections={}
    for tag,body in sf2_chunks(raw,12,len(raw)):
        if tag!=b"LIST" or len(body)<4:continue
        for key,val in sf2_chunks(body,4,len(body)):
            sections[(body[:4],key)]=val
    def required(group,key,width):
        v=sections.get((group,key),b"")
        if not v or len(v)%width:raise ValueError("Missing/misaligned SoundFont "+str(key))
        return v
    header=required(b"pdta",b"phdr",38)
    inst=required(b"pdta",b"inst",22)
    samples=required(b"pdta",b"shdr",46)
    rawpcm=required(b"sdta",b"smpl",2)
    count=len(header)//38-1
    if count!=TOTAL_PRESETS:raise ValueError("Wrong preset count: "+str(count))
    output={}
    for i in range(count):
        item=header[i*38:(i+1)*38]
        name=item[:20].split(b"\0")[0].decode("latin1","replace")
        program,bank=struct.unpack_from("<HH",item,20)
        if bank!=0:raise ValueError("Unexpected preset bank "+str(bank))
        if program in output:raise ValueError("Duplicate MIDI program "+str(program))
        output[program]=name
    if set(output)!=PROGRAMS:
        raise ValueError("Program set differs; missing/extra: "+str(sorted(PROGRAMS.symmetric_difference(output))))
    for p,name in KNOWN.items():
        if output[p]!=name:
            raise ValueError("Critical bass mismatch at program "+str(p))
    return {"phase":"P80","original_sf2_integrity":"full 77-preset bank",
            "file_bytes":len(raw),"sample_data_bytes":len(rawpcm),
            "sample_data_kib":round(len(rawpcm)/1024,2),
            "instrument_count":len(inst)//22-1,
            "sample_header_count":len(samples)//46-1,
            "bank":0,"preset_count":count,
            "program_count":len(output),"missing_program":63,
            "presets":[{"program":p,"name":output[p]} for p in sorted(output)],
            "sample_content_exported":False,
            "audio_synthesized":False,
            "full_creative_driver_load_proven":False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf2",required=True,type=Path)
    parser.add_argument("--report",type=Path)
    args=parser.parse_args()
    report=inventory(args.sf2.read_bytes())
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
