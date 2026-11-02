#!/usr/bin/env python3
"""P89: compare NOTE-triggered original Creative Win95 and native EMU8000 I/O.

Inputs: P45 original-86Box CSV and Emu8000Core::OpenTrace text. Captures
MUST come from an identical SF2, MIDI program/note/velocity and driver setup.
The Win95 trace is isolated by measured zero-based CSV DATA ROW offsets;
the native trace must be opened AFTER bank upload and program selection.
Ignores pointers, host polling and sample-memory writes (they are not voices).
Does not turn hardware-emulator agreement into a real physical-card claim.
"""
from __future__ import annotations
import argparse,collections,csv,hashlib,json
from pathlib import Path

# Absolute ISA I/O addresses with standard SB base port 0x220.
PORTS={0x620:"DATA0",0x622:"DATA0HI",0xA20:"DATA1",0xA22:"DATA1HI",
       0xE20:"DATA3",0xE22:"POINTER"}
# Voice programming registers explicitly worth measuring first.
NAMES={
 ("DATA1",4):"ATKHLDV", ("DATA1",5):"LFO1VAL",
 ("DATA1",6):"ATKHLD", ("DATA1",7):"LFO2VAL",
 ("DATA1",0):"CCCA_LO",("DATA1HI",0):"CCCA_HI",
 ("DATA1",2):"DCYSUSV",("DATA1",3):"DCYSUS",
 ("DATA0",0):"PTRX_LO",("DATA0HI",0):"PTRX_HI",
 ("DATA0",1):"CPF_LO",("DATA0HI",1):"CPF_HI",
 ("DATA0",2):"CVCF_LO",("DATA0HI",2):"CVCF_HI",
 ("DATA0",3):"VTFT_LO",("DATA0HI",3):"VTFT_HI",
 ("DATA0",4):"PSST_LO",("DATA0HI",4):"PSST_HI",
 ("DATA0",5):"CSL_LO",("DATA0HI",5):"CSL_HI",
}
# Unlabeled registers retain a stable port+reg identity in diagnostics.

def normalized(port,value,pointer):
    port_type=PORTS.get(port)
    if port_type is None or port_type=="POINTER":return None
    voice=pointer&31
    register=(pointer>>5)&7
    if voice>=32:return None
    # Sample RAM DMA upload via voice 26/register1 on A20/A22.
    if voice==26 and register==1 and port_type in ("DATA1","DATA1HI"):
        return None
    name=NAMES.get((port_type,register),f"{port_type}:R{register}")
    return voice,name,value

def original_csv(path,start,end):
    if start<0 or end<=start:raise ValueError("Original Creative note I/O boundaries are invalid")
    if not Path(path).is_file():raise FileNotFoundError(path)
    out=[]
    with open(path,newline="",encoding="utf8") as source:
        rows=csv.DictReader(source)
        for index,row in enumerate(rows):
            if index<start:continue
            if index>=end:break
            if row.get("kind")!="data":continue
            try:
                item=normalized(int(row["port"],16),int(row["value"],16),
                                int(row["pointer"],16))
            except (KeyError,TypeError,ValueError) as exc:
                raise ValueError(f"Malformed Creative row {index}") from exc
            if item:out.append(item)
        if index+1<end:raise ValueError("Creative trace shorter than declared note window")
    if not out:raise ValueError("Original Creative note window contains no voice writes")
    return out

def native_trace(path):
    out=[]
    pointer=None
    with open(path,encoding="utf8") as file:
        for line in file:
            line=line.strip()
            if not line or line.startswith("#") or line.startswith("R "):continue
            words=line.split()
            if len(words)!=3:raise ValueError("Malformed native port-write line: "+line[:100])
            try: _,port_hex,value_hex=words;port=int(port_hex,16);value=int(value_hex,16)
            except ValueError as exc:raise ValueError("Malformed native hex I/O") from exc
            if port==0xE22:
                pointer=value
            elif port in PORTS:
                if pointer is None:raise ValueError("Native data write before register pointer")
                item=normalized(port,value,pointer)
                if item:out.append(item)
    if not out:raise ValueError("Native note trace contains no voice writes")
    return out

def compare(original,native):
    if not original or not native:raise ValueError("Need both independent note-on traces")
    # Keep per-register write histories, not the aggregate final state alone.
    # Normalize voice allocations by ORDER OF FIRST VOICE USE, to prevent
    # different free-voice selection from causing wholly spurious mismatches.
    def groups(seq):
        mapping={}
        rows=collections.defaultdict(list)
        for voice,name,value in seq:
            if voice not in mapping:mapping[voice]=len(mapping)
            rows[(mapping[voice],name)].append(value)
        return rows,mapping
    a,voices_a=groups(original);b,voices_b=groups(native)
    labels=sorted(set(a)|set(b))
    mismatches=[]
    identical=0
    for voice,name in labels:
        va=a.get((voice,name),[]);vb=b.get((voice,name),[])
        if va==vb:identical+=1;continue
        # No proprietary PCM or full trace is exposed. Only ≤4 diagnostic
        # register words per mismatch, for actionable source-level debugging.
        mismatches.append({"voice_slot":voice,"register":name,
                           "creative_writes":len(va),"native_writes":len(vb),
                           "creative_first":[f"0x{x:04X}" for x in va[:4]],
                           "native_first":[f"0x{x:04X}" for x in vb[:4]],
                           "first_different_index":next((i for i in range(min(len(va),len(vb)))
                                                         if va[i]!=vb[i]),min(len(va),len(vb)))})
    return {"original_creative_note_register_writes":len(original),
            "native_note_register_writes":len(native),
            "creative_active_voice_count":len(voices_a),
            "native_active_voice_count":len(voices_b),
            "register_series_compared":len(labels),
            "register_series_exactly_equal":identical,
            "register_series_different":len(mismatches),
            "mismatches":mismatches[:100],
            "mismatches_truncated":max(0,len(mismatches)-100),
            "emulated_hardware_1to1_proven":len(mismatches)==0,
            "physical_hardware_parity_proven":False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--creative-csv",required=True,type=Path)
    parser.add_argument("--native-trace",required=True,type=Path)
    parser.add_argument("--creative-start",required=True,type=int,
                        help="0-based P45 CSV row count immediately BEFORE the note-on")
    parser.add_argument("--creative-end",required=True,type=int,
                        help="0-based P45 CSV row count immediately AFTER the note-on")
    parser.add_argument("--creative-guest-report",required=True,type=Path)
    parser.add_argument("--sf2-sha256",required=True,
                        help="Identical original SF2 hash required at both capture endpoints")
    parser.add_argument("--midi-program",type=int,default=0)
    parser.add_argument("--midi-note",type=int,default=48)
    parser.add_argument("--midi-velocity",type=int,default=100)
    parser.add_argument("--out",required=True,type=Path)
    a=parser.parse_args()
    if not (0<=a.midi_program<128 and 0<=a.midi_note<128 and 1<=a.midi_velocity<=127):
        raise ValueError("Invalid MIDI test fixture")
    if len(a.sf2_sha256)!=64 or any(c not in "0123456789abcdef" for c in a.sf2_sha256):
        raise ValueError("Original SF2 SHA-256 must be lowercase 64 hex characters")
    guest=json.loads(a.creative_guest_report.read_text(encoding="utf8"))
    required=("agent_launched_in_actual_win95","original_creative_winmm_endpoint_selected",
              "p75_sf2_sample_upload_plausible")
    if not all(guest.get(k) for k in required):
        raise ValueError("Original Win95 Creative driver/SF2 upload was not established")
    ref=original_csv(a.creative_csv,a.creative_start,a.creative_end)
    native=native_trace(a.native_trace)
    result={"phase":"P89","source_sf2_sha256":a.sf2_sha256,
            "midi":{"bank":0,"program":a.midi_program,"note":a.midi_note,"velocity":a.midi_velocity},
            "original_win95_creative_agent_verified":True,
            "comparison":compare(ref,native)}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print(f"P89: compared {result['comparison']['register_series_compared']} voice register series; "
          f"{result['comparison']['register_series_different']} differ")
    # A difference means report a finding, not a failed test-runner execution.
    # Missing genuine evidence MUST fail closed before producing a parity verdict.

if __name__=="__main__":main()
