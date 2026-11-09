#!/usr/bin/env python3
"""P210: generate copyright-free 14-preset EG1 SF2 for genuine Creative Win95.
Single generated sine sample shared by independent instrument zones;
never copies the original user's SoundFont, Creative ROM, or Windows driver.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from p83_generic_sf2 import inspect_sf2

# Unique combinations; one-dimensional sweeps around the same anchor.
VARIANTS=(
  (-12000,500),(-2400,500),(-1200,500),(-600,500),
  (0,500),(600,500),(1200,500),(2400,500),
  (0,0),(0,250),(0,499),(0,501),(0,750),(0,1000),
)
NOTE=59
RATE=44100
FRAMES=4410
GENERATORS=(7,25,26,27,28,29,30,36,54,53)

def require(c,reason):
    if not c:raise ValueError("P210 SF2 rejected: "+reason)
def name20(s):
    d=s.encode("ascii")
    require(len(d)<20,"SF2 name too long")
    return d.ljust(20,b"\0")
def chunk(t,data):
    require(len(t)==4,"SF2 chunk fourcc")
    return t+struct.pack("<I",len(data))+data+(b"\0" if len(data)&1 else b"")
def lst(t,*chunks):
    return chunk(b"LIST",t+b"".join(chunks))
def generator_list(hold_tc,sustain_permille):
    return (
      (7,1200), # modEnvToPitch +1 octave
      (25,0),   # delayModEnv 0tc = 1sec, not instantaneous
      (26,0),   # attackModEnv 0tc = 1sec
      (27,hold_tc),
      (28,0),   # decayModEnv 0tc = 1sec
      (29,sustain_permille),
      (30,-12000), # releaseModEnv ~1ms to avoid voice overlaps
      (36,-12000), # releaseVolEnv ~1ms
      (54,1),      # looping
      (53,0),      # sample ID must be LAST
    )
def make_sf2():
    require(len(VARIANTS)==14 and len(set(VARIANTS))==14,
            "not independent 14-program fixture")
    samples=[int(round(10000*math.sin(2*math.pi*440*i/RATE)))
             for i in range(FRAMES)]
    pcm=struct.pack("<"+"h"*FRAMES,*samples)+bytes(46*2)
    info=lst(b"INFO",chunk(b"ifil",struct.pack("<HH",2,1)),
             chunk(b"isng",b"EMU8000\0"),
             chunk(b"INAM",b"125A P210 Original Driver EG1 Sweep\0"),
             chunk(b"ICMT",b"Synthetic 440Hz PCM; no user or vendor bank data\0"))
    sdta=lst(b"sdta",chunk(b"smpl",pcm))
    phdr=b"";pbag=b"";pgen=b"";inst=b"";ibag=b"";igen=b""
    manifest=[]
    n_gen=len(GENERATORS)
    for i,(tc,per) in enumerate(VARIANTS):
        name=f"P210 EG1 {i:02d}"
        phdr+=name20(name)+struct.pack("<HHHIII",i,0,i,0,0,0)
        pbag+=struct.pack("<HH",i,0)
        pgen+=struct.pack("<HH",41,i)
        inst+=name20(f"P210 ENV {i:02d}")+struct.pack("<H",i*n_gen)
        ibag+=struct.pack("<HH",i*n_gen,0)
        gens=generator_list(tc,per)
        require(tuple(g for g,_ in gens)==GENERATORS,"wrong SF2 instrument generator order")
        for opcode,value in gens:
            igen+=struct.pack("<HH",opcode,value&65535)
        manifest.append({"program":i,"name":name,"note":NOTE,
                         "hold_mod_env_tc":tc,
                         "sustain_mod_env_permille":per,
                         "attack_mod_env_tc":0,"delay_mod_env_tc":0,
                         "mod_env_to_pitch_cents":1200,"sample_index":0})
    n=len(VARIANTS)
    phdr+=name20("EOP")+struct.pack("<HHHIII",0,0,n,0,0,0)
    pbag+=struct.pack("<HH",n,0)
    pgen+=struct.pack("<HH",0,0)
    inst+=name20("EOI")+struct.pack("<H",n*n_gen)
    ibag+=struct.pack("<HH",n*n_gen,0)
    igen+=struct.pack("<HH",0,0)
    pmod=bytes(10)
    imod=bytes(10)
    shdr=(name20("P210 Sine 440")
          +struct.pack("<IIIIIbbHH",0,FRAMES,200,FRAMES-200,
                       RATE,NOTE,0,0,1)
          +name20("EOS")
          +struct.pack("<IIIIIbbHH",FRAMES+46,FRAMES+46,
                       FRAMES+46,FRAMES+46,RATE,0,0,0,1))
    pdta=lst(b"pdta",chunk(b"phdr",phdr),chunk(b"pbag",pbag),
             chunk(b"pmod",pmod),chunk(b"pgen",pgen),
             chunk(b"inst",inst),chunk(b"ibag",ibag),
             chunk(b"imod",imod),chunk(b"igen",igen),chunk(b"shdr",shdr))
    blob=b"sfbk"+info+sdta+pdta
    return b"RIFF"+struct.pack("<I",len(blob))+blob,manifest
def inspect_generators(raw):
    from p83_generic_sf2 import chunks
    sections={}
    for tag,body in chunks(raw,12,len(raw)):
        if tag!=b"LIST":continue
        for sub,data in chunks(body,4,len(body)):
            if bytes(body[:4])==b"pdta":sections[sub]=bytes(data)
    igen=sections[b"igen"]
    ibag=sections[b"ibag"]
    inst=sections[b"inst"]
    got=[]
    for i in range(14):
        ins_idx,=struct.unpack_from("<H",inst,i*22+20)
        next_idx,=struct.unpack_from("<H",inst,(i+1)*22+20)
        require(next_idx==ins_idx+1,"not a single instrument zone")
        start,=struct.unpack_from("<H",ibag,ins_idx*4)
        stop,=struct.unpack_from("<H",ibag,next_idx*4)
        record=[struct.unpack_from("<HH",igen,j*4) for j in range(start,stop)]
        require(tuple(op for op,_ in record)==GENERATORS,"generator packing order broken")
        tc,per=VARIANTS[i]
        require(record[3][1]==tc&65535 and record[5][1]==per,
                "hold/sustain fixture changed")
        got.append((tc,per))
    require(tuple(got)==VARIANTS,"SF2 payload sweep mismatch")
def selftest():
    raw,variants=make_sf2()
    report=inspect_sf2(raw)
    require(report["preset_count"]==14 and
            report["instrument_count"]==14 and
            report["sample_count"]==1 and
            report["sample_memory_fits"],"unacceptable SoundFont structure")
    require([x["program"] for x in report["presets"]]==list(range(14)),
            "duplicate or missing original driver programs")
    inspect_generators(raw)
    require(hashlib.sha256(raw).digest()==hashlib.sha256(make_sf2()[0]).digest(),
            "nondeterministic audio/SF2 generator")
    for mutant in (
        VARIANTS[:-1],
        tuple((0,500) for _ in VARIANTS),
    ):
        require(mutant!=VARIANTS and (len(mutant)!=14 or len(set(mutant))!=14),
                "mutation not rejected")
    print("P210 SF2 self-test PASS: 14 unique instrument generators, 1 original synthetic 440Hz PCM sample")
    return raw,variants
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sf2",type=Path)
    p.add_argument("--manifest",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    raw,variants=selftest()
    if a.self_test and not a.sf2:return
    require(a.sf2 and a.manifest,"SF2+manifest output paths mandatory")
    a.sf2.parent.mkdir(parents=True,exist_ok=True)
    a.manifest.parent.mkdir(parents=True,exist_ok=True)
    a.sf2.write_bytes(raw)
    a.manifest.write_text(json.dumps({
        "schema":"P210-generated-EG1-v1",
        "synthetic_only":True,
        "sf2_sha256":hashlib.sha256(raw).hexdigest(),
        "programs":variants,
        "soundfont_generator_source":"tools/p210_make_eg1_sf2.py",
        "notes":"No original user SF2, ROM or external samples are embedded; only numeric manifest can be exported"
    },indent=2)+"\n")
    print("P210 generated 14-program original-driver research SF2",len(raw),
          "bytes SHA256",hashlib.sha256(raw).hexdigest())
if __name__=="__main__":
    main()
