#!/usr/bin/env python3
"""P196: read-only RIFF/SF2 preset/instrument generator inventory.
Used to verify the scaleTuning/KeynumToHold hypothesis against the SHA-pinned
public SoundFont Spec Test, without exporting any audio or soundbank bytes.
"""
import argparse
import json
from pathlib import Path
import struct

OPS = {7:"modEnvToPitch",8:"initialFilterFc",9:"initialFilterQ",
       25:"delayModEnv",26:"attackModEnv",27:"holdModEnv",28:"decayModEnv",
       29:"sustainModEnv",30:"releaseModEnv",
       33:"delayVolEnv",34:"attackVolEnv",35:"holdVolEnv",
       36:"decayVolEnv",37:"sustainVolEnv",38:"releaseVolEnv",
       39:"keynumToVolEnvHold",40:"keynumToVolEnvDecay",
       41:"instrument",43:"keyRange",46:"keynum",47:"velocity",
       48:"initialAttenuation",51:"coarseTune",52:"fineTune",
       53:"sampleID",54:"sampleModes",56:"scaleTuning",
       58:"overridingRootKey"}


def chunks(data, start, end):
    at = start
    while at + 8 <= end:
        tag, size = struct.unpack_from("<4sI", data, at)
        begin, stop = at + 8, at + 8 + size
        if stop > end:
            raise ValueError("Truncated chunk")
        yield tag, begin, stop
        at = stop + (size & 1)
    if at != end:
        raise ValueError("Chunk alignment mismatch")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sf2", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--programs", default="1,2",
                   help="Comma-separated original bank 0 program IDs to inspect")
    a = p.parse_args()
    selected = {int(x) for x in a.programs.split(",")}
    if any(i<0 or i>127 for i in selected):
        raise ValueError("Invalid program")
    data = Path(a.sf2).read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"sfbk":
        raise ValueError("Not a RIFF SoundFont bank")
    end = 8 + struct.unpack_from("<I",data,4)[0]
    if end > len(data):
        raise ValueError("Bad RIFF length")
    pdta = {}
    for tag,lo,hi in chunks(data,12,end):
        if tag == b"LIST" and data[lo:lo+4] == b"pdta":
            pdta = {name:data[st:en] for name,st,en in chunks(data,lo+4,hi)}
    need=(b"phdr",b"pbag",b"pgen",b"inst",b"ibag",b"igen")
    if not all(x in pdta for x in need):
        raise ValueError("Missing SF2 pdta generators")
    for key,n in ((b"phdr",38),(b"pbag",4),(b"pgen",4),
                  (b"inst",22),(b"ibag",4),(b"igen",4)):
        if len(pdta[key]) % n:
            raise ValueError("Bad pdta record size: "+str(key))
    def genlist(table):
        return [struct.unpack_from("<Hh",table,i) for i in range(0,len(table),4)]
    def bags(table):
        return [struct.unpack_from("<HH",table,i) for i in range(0,len(table),4)]
    pgen=genlist(pdta[b"pgen"]); igen=genlist(pdta[b"igen"])
    pbag=bags(pdta[b"pbag"]); ibag=bags(pdta[b"ibag"])
    phdr=[]
    for n in range(0,len(pdta[b"phdr"]),38):
        name,program,bank,idx=struct.unpack_from("<20sHHH",pdta[b"phdr"],n)
        phdr.append((name.split(b"\0")[0].decode("ascii","replace"),program,bank,idx))
    inst=[]
    for n in range(0,len(pdta[b"inst"]),22):
        name,idx=struct.unpack_from("<20sH",pdta[b"inst"],n)
        inst.append((name.split(b"\0")[0].decode("ascii","replace"),idx))
    def zonelist(bags_,gens_,start,stop):
        out=[]
        for i in range(start,stop):
            beg=bags_[i][0];end=bags_[i+1][0]
            if beg>end or end>len(gens_):
                raise ValueError("Invalid zone generators")
            mapped={}
            for op,val in gens_[beg:end]:
                if op in OPS:
                    if op == 43:
                        value=[val&255,(val>>8)&255]
                    elif op in (41,53):
                        value=val&65535
                    else:
                        value=val
                    mapped[OPS[op]]=value
            out.append({"zone":i-start,"generator":mapped})
        return out
    result=[]
    for k in range(len(phdr)-1):
        name,prog,bank,idx=phdr[k]
        if bank != 0 or prog not in selected:
            continue
        pzones=zonelist(pbag,pgen,idx,phdr[k+1][3])
        ins=[]
        for zone in pzones:
            iid=zone["generator"].get("instrument")
            if iid is None: continue
            if iid>=len(inst)-1:
                raise ValueError("Invalid instrument ID")
            ins.append({"name":inst[iid][0],"id":iid,
                        "zones":zonelist(ibag,igen,inst[iid][1],inst[iid+1][1])})
        result.append({"program":prog,"name":name,"bank":bank,
                       "preset_zones":pzones,"instruments":ins})
    if {r["program"] for r in result} != selected:
        raise ValueError("Requested SoundFont programs missing or ambiguous: "+str(selected))
    for item in result:
        scale=[z["generator"].get("scaleTuning") for i in item["instruments"]
               for z in i["zones"] if "scaleTuning" in z["generator"]]
        print("P197 program",item["program"],item["name"],
              "instrument scaleTuning values",scale,
              "all special generators",
              [(i["name"],z["generator"]) for i in item["instruments"] for z in i["zones"]])
    Path(a.out).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
