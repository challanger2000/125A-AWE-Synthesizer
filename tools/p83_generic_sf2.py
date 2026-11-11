#!/usr/bin/env python3
"""P83: accept ANY structurally valid, hardware-sized SF2, not one named bank.

Real SF2 file header/INFO/smpl/phdr/inst/shdr are inspected without changing
the PCM, presets, or instrument parameters. Stage into a private Win95 FAT
disk for the ORIGINAL Creative AWE driver. This is not a synth/render engine.
"""
from __future__ import annotations
import argparse
import json
import struct
from pathlib import Path

GUEST_PATH="AWE32/P83USER.SF2"  # Win95-safe 8.3 path
RAM_BYTES={"awe32":2048*1024,"awe64_gold":28672*1024}
RECORD_BYTES={b"phdr":38,b"pbag":4,b"pmod":10,b"pgen":4,
              b"inst":22,b"ibag":4,b"imod":10,b"igen":4,b"shdr":46}

def chunks(src,begin,end):
    pos=begin
    while pos+8<=end:
        tag=bytes(src[pos:pos+4])
        length,=struct.unpack_from("<I",src,pos+4)
        end_data=pos+8+length
        if end_data>end:raise ValueError("Truncated SF2 chunk "+str(tag))
        yield tag,src[pos+8:end_data]
        pos=end_data+(length&1)
    if pos!=end:raise ValueError("Invalid RIFF chunk padding/alignment")

def inspect_sf2(raw,ram_bytes=RAM_BYTES["awe64_gold"]):
    if not isinstance(raw,(bytes,bytearray,memoryview)):
        raise TypeError("SF2 input must be binary")
    data=memoryview(raw)
    if len(data)<64 or bytes(data[:4])!=b"RIFF" or bytes(data[8:12])!=b"sfbk":
        raise ValueError("Not an SF2 RIFF/sfbk SoundFont")
    length,=struct.unpack_from("<I",data,4)
    if length+8!=len(data):raise ValueError("RIFF length mismatch")
    sections={}
    for tag,body in chunks(data,12,len(data)):
        if tag!=b"LIST":continue
        if len(body)<4:raise ValueError("Empty SF2 LIST")
        list_type=bytes(body[:4])
        for key,val in chunks(body,4,len(body)):
            id=(list_type,key)
            if id in sections:raise ValueError("Duplicated SF2 section "+str(id))
            sections[id]=val
    ifil=sections.get((b"INFO",b"ifil"))
    if not ifil or len(ifil)!=4:raise ValueError("Missing INFO/ifil version")
    major,minor=struct.unpack_from("<HH",ifil,0)
    if major!=2:raise ValueError("Unsupported SoundFont version "+str(major))
    needed={}
    for name,width in RECORD_BYTES.items():
        val=sections.get((b"pdta",name))
        if val is None or len(val)<width or len(val)%width:
            raise ValueError("Missing/misaligned SF2 pdta/"+name.decode("ascii"))
        needed[name]=val
    samples=sections.get((b"sdta",b"smpl"))
    if samples is None or len(samples)==0 or len(samples)%2:
        raise ValueError("Missing/odd-length SF2 16-bit smpl data")
    sf24=sections.get((b"sdta",b"sm24"))
    smpl_bytes=len(samples)
    max_bytes=ram_bytes if ram_bytes is not None else None
    if max_bytes is not None and max_bytes<=0:raise ValueError("Invalid emulated RAM size")
    presets=[]
    phdr=needed[b"phdr"]
    if len(phdr)<76 or bytes(phdr[-38:-35])!=b"EOP":
        raise ValueError("No valid terminal EOP preset header")
    for i in range(len(phdr)//38-1):
        off=i*38
        name=bytes(phdr[off:off+20]).split(b"\0",1)[0].decode("latin1")
        number,bank=struct.unpack_from("<HH",phdr,off+20)
        if not 0<=number<128:raise ValueError("SF2 program outside MIDI 0-127")
        presets.append({"bank":bank,"program":number,"name":name,
                        "percussion_bank":bank==128})
    if not presets:raise ValueError("SF2 has no presets")
    ins=needed[b"inst"];shdr=needed[b"shdr"]
    if len(ins)<44 or bytes(ins[-22:-19])!=b"EOI":
        raise ValueError("No terminal EOI instrument header")
    if len(shdr)<92 or bytes(shdr[-46:-43])!=b"EOS":
        raise ValueError("No terminal EOS sample header")
    count=len(shdr)//46-1
    rom_samples=0
    for i in range(count):
        off=i*46
        start,end=struct.unpack_from("<II",shdr,off+20)
        sample_type,=struct.unpack_from("<H",shdr,off+44)
        # SF2 ROM sample addresses refer to the original 1MiB EMU8000
        # wave ROM, not to this file's smpl chunk. Vintage Dreams' SineWave
        # is a real example. Keep the original bytes and validate each
        # address against its actual source memory.
        in_rom=bool(sample_type&0x8000)
        rom_samples+=in_rom
        limit=1048576//2 if in_rom else smpl_bytes//2
        if start>end or end>limit:
            raise ValueError("Sample %d reaches beyond %s"%
                             (i,"1MiB wave ROM" if in_rom else "smpl data"))
    fits=(max_bytes is None or smpl_bytes<=max_bytes)
    return {"phase":"P83","sf2_valid":True,"sf2_version":f"{major}.{minor:02d}",
            "file_bytes":len(data),"sample_pcm_bytes":smpl_bytes,
            "sample_pcm_mib":round(smpl_bytes/1048576,3),
            "sample_memory_limit_bytes":max_bytes,
            "sample_memory_fits":fits,
            "sample_memory_remaining_bytes":None if max_bytes is None else max_bytes-smpl_bytes,
            "sm24_extension_present":sf24 is not None,
            "instrument_count":len(ins)//22-1,"sample_count":count,
            "rom_sample_count":rom_samples,
            "preset_count":len(presets),
            "available_banks":sorted({p["bank"] for p in presets}),
            "drum_bank_present":any(p["bank"]==128 for p in presets),
            "presets":presets,"samples_rewritten":False,
            "creative_driver_playback_verified":False}

def stage_private(disk,sf2,ram_bytes=RAM_BYTES["awe64_gold"]):
    from pyfatfs.PyFatFS import PyFatFS
    from p38_stage_creative_awe32_win95 import partition_offset
    data=Path(sf2).read_bytes()
    report=inspect_sf2(data,ram_bytes=ram_bytes)
    if not report["sample_memory_fits"]:
        raise ValueError("SF2 needs %.2f MiB PCM but emulated card has %.2f MiB RAM"
                         %(report["sample_pcm_bytes"]/1048576,ram_bytes/1048576))
    # Do not modify any audio bytes, sample zones, banks or names.
    with PyFatFS(str(disk),offset=partition_offset(disk),
                 read_only=False,preserve_case=False) as fs:
        fs.makedirs("AWE32",recreate=True)
        with fs.openbin(GUEST_PATH,"w") as stream:stream.write(data)
        if fs.readbytes(GUEST_PATH)!=data:
            raise IOError("Guest SF2 differs from source")
    report["original_bytes_staged"]=True
    report["guest_file"]="C:\\AWE32\\P83USER.SF2"
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sf2",required=True,type=Path)
    parser.add_argument("--card",choices=tuple(RAM_BYTES),default="awe64_gold")
    parser.add_argument("--disk",type=Path)
    parser.add_argument("--report",type=Path)
    opts=parser.parse_args()
    ram=RAM_BYTES[opts.card]
    result=(stage_private(opts.disk,opts.sf2,ram)
            if opts.disk else inspect_sf2(opts.sf2.read_bytes(),ram))
    result["card"]=opts.card
    if opts.report:
        opts.report.parent.mkdir(parents=True,exist_ok=True)
        opts.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result["sample_memory_fits"]:raise SystemExit(2)
if __name__=="__main__":
    main()
