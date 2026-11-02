#!/usr/bin/env python3
"""P75: verify original private SF2 presets and stage only into ephemeral Win95 FAT.

Never commit or upload SoundFont bytes, user sample data or rendered audio.
"""
import argparse
import json
import struct
from pathlib import Path

GUEST_PATH = "AWE32/P75USER.SF2"
EXPECTED = {0:"Grungy Ramp Bass",7:"TX81Z Lately Bass"}

def chunks(data,start,end):
    pos=start
    while pos+8<=end:
        tag=data[pos:pos+4]
        n,=struct.unpack_from("<I",data,pos+4)
        to=pos+8+n
        if to>end:
            raise ValueError("Truncated RIFF chunk")
        yield tag,data[pos+8:to]
        pos=to+(n&1)
    if pos!=end:
        raise ValueError("RIFF alignment mismatch")

def inspect(raw):
    if len(raw)<64 or raw[:4]!=b"RIFF" or raw[8:12]!=b"sfbk":
        raise ValueError("Not a SoundFont 2 RIFF")
    n,=struct.unpack_from("<I",raw,4)
    if n+8!=len(raw):
        raise ValueError("RIFF length mismatch")
    sections={}
    for tag,val in chunks(raw,12,len(raw)):
        if tag==b"LIST" and len(val)>=4:
            for sub,part in chunks(val,4,len(val)):
                sections[(val[:4],sub)]=part
    phdr=sections.get((b"pdta",b"phdr"),b"")
    smpl=sections.get((b"sdta",b"smpl"),b"")
    if len(phdr)<76 or len(phdr)%38 or not smpl or len(smpl)%2:
        raise ValueError("Incomplete SF2 preset/sample chunks")
    presets={}
    count=len(phdr)//38-1
    for i in range(count):
        item=phdr[38*i:38*(i+1)]
        name=item[:20].split(b"\0")[0].decode("latin1")
        program,bank=struct.unpack_from("<HH",item,20)
        if bank==0:
            presets[program]=name
    for p,name in EXPECTED.items():
        if presets.get(p)!=name:
            raise ValueError("Wrong SF2: MIDI program %d expected %r, got %r"%(p,name,presets.get(p)))
    return {"phase":"P75","sf2_valid":True,"preset_count":count,
            "sample_data_bytes":len(smpl),"presets":{str(k):v for k,v in EXPECTED.items()},
            "original_sf2_staged":False,"private_file_uploaded":False}

def stage(disk,sf2):
    from pyfatfs.PyFatFS import PyFatFS
    from p38_stage_creative_awe32_win95 import partition_offset
    data=Path(sf2).read_bytes()
    result=inspect(data)
    with PyFatFS(str(disk),offset=partition_offset(disk),
                 read_only=False,preserve_case=False) as fs:
        fs.makedirs("AWE32",recreate=True)
        with fs.openbin(GUEST_PATH,"w") as f:
            f.write(data)
        if fs.readbytes(GUEST_PATH)!=data:
            raise AssertionError("Private SF2 guest staging mismatch")
    result["original_sf2_staged"]=True
    result["guest_file"]="C:\\AWE32\\P75USER.SF2"
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sf2",type=Path,required=True)
    ap.add_argument("--disk",type=Path)
    ap.add_argument("--report",type=Path)
    args=ap.parse_args()
    result=stage(args.disk,args.sf2) if args.disk else inspect(args.sf2.read_bytes())
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
