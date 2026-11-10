#!/usr/bin/env python3
"""P227: original Win95 Creative FX CC91/CC93 send registers + 86Box audio.

Uses the EXISTING proven P48/P63/P64/P65/P67 original 86Box Win95 guest,
Creative WinMM AWE Synth endpoint and actual Creative bank loader.
Research-only PUBLIC authenticated SoundFont-Spec-Test, NOT owner's 77-bank.
The sound engine is never replaced by our native Synth or injected registers.
No guest, ROM, driver or original media is uploaded to a public artifact.
"""
from __future__ import annotations
import array
import hashlib
import math
import os
import sys
import wave
from pathlib import Path

from p63_send_guest_midi import frame
from p64_original_win95_midi_trial import (
    connect_linux_86box_fifo, send_paced_frame
)
from p65_pcm_receiver import PcmReceiver
from p89_compare_voice_registers import original_csv

PROGRAMS = (0, 1)             # original public accepted SoundFont v3.0
VELOCITIES = (64, 120)
NOTE = 59                     # the source's independently checked sample43
BANK = 1                     # Creative AWECP user-bank selected by CC0
CHANNEL = 0
FX = ((0, 0), (127, 0), (0, 127), (127, 127))
SCHEMA = "125A-P227-original-Win95-Creative-CC91-93-16-v1"

def matrix():
    return tuple(dict(program=pr, note=NOTE, velocity=vel,
                      cc91=rev, cc93=cho, stage=stage,
                      id=f"P{pr:03d}-N{NOTE}V{vel}-{stage}")
                 for pr in PROGRAMS for vel in VELOCITIES
                 for stage,(rev,cho) in enumerate(FX))

def require(cond, msg):
    if not cond: raise ValueError("P227 REAL ORIGINAL CREATIVE PROOF FAIL: "+msg)

def counts(path):
    if not Path(path).is_file(): return -1
    with open(path,"r",encoding="utf8",errors="replace") as file:
        return max(-1,sum(1 for _ in file)-1)

def original_sends(register_writes):
    """Preserve the actual byte on every real note voice, not a predicted CC law.
    PTRX_LO high byte carries reverb. CSL_HI high byte carries chorus.
    Multiple writes/voices are preserved; never treat voice26 DRAM IO as a voice.
    """
    rev=[(voice,(value>>8)&255) for voice,name,value in register_writes
         if name=="PTRX_LO" and voice!=26]
    cho=[(voice,(value>>8)&255) for voice,name,value in register_writes
         if name=="CSL_HI" and voice!=26]
    starts=[voice for voice,name,value in register_writes if name=="PSST_LO" and voice!=26]
    require(starts and rev and cho, "real note must program PSST, PTRX and CSL")
    active=set(starts)
    rev=[(voice,send) for voice,send in rev if voice in active]
    cho=[(voice,send) for voice,send in cho if voice in active]
    require(rev and cho, "no matching send register on actual started sample voice")
    return {
        "started_voices":sorted(active),
        "reverb_register_writes":rev[:24],
        "chorus_register_writes":cho[:24],
        "reverb_first_by_voice":{str(v):next(x for voice,x in rev if voice==v)
                                 for v in sorted({voice for voice,_ in rev})},
        "chorus_first_by_voice":{str(v):next(x for voice,x in cho if voice==v)
                                 for v in sorted({voice for voice,_ in cho})},
    }

def pcm_statistics(path):
    """Analyse original 86Box Wavetable 44.1 kHz stereo PCM16 (no normalisation)."""
    square=[0.0,0.0]
    total=[0,0]
    peak=0
    neg=pos=nonzero=0
    with wave.open(str(path),"rb") as f:
        channels=f.getnchannels(); width=f.getsampwidth()
        rate=f.getframerate(); frames=f.getnframes()
        require((channels,width,rate,f.getcomptype())==(2,2,44100,"NONE"),
                "not actual 86Box 44.1kHz stereo wavetable signed16")
        require(44100<=frames<=44100*10,"guest PCM capture length wrong")
        while True:
            data=f.readframes(8192)
            if not data:break
            samples=array.array("h")
            samples.frombytes(data)
            if sys.byteorder!="little":samples.byteswap()
            require(len(samples)%2==0,"partial PCM frame")
            for ch in (0,1):
                x=samples[ch::2]
                total[ch]+=sum(x)
                square[ch]+=sum(float(v)*v for v in x)
                peak=max(peak,max((abs(v) for v in x),default=0))
                neg+=sum(v==-32768 for v in x)
                pos+=sum(v==32767 for v in x)
            nonzero+=sum(samples[i]!=0 or samples[i+1]!=0
                         for i in range(0,len(samples),2))
    require(nonzero>0,"original Creative real-bank test played DIGITAL SILENCE")
    return dict(frames=frames,nonzero_frames=nonzero,
                rms=[math.sqrt(x/frames)/32768 for x in square],
                dc=[x/frames/32768 for x in total],
                peak=peak/32768,neg_rail=neg,pos_rail=pos,
                wav_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest())

def test_matrix():
    cases=matrix()
    require(len(cases)==16 and len({c["id"] for c in cases})==16,
            "matrix must have 16 unique cases")
    for p in PROGRAMS:
        for vel in VELOCITIES:
            sub=[c for c in cases if c["program"]==p and c["velocity"]==vel]
            require(len(sub)==4 and [(c["cc91"],c["cc93"]) for c in sub]==list(FX),
                    "four independent CC-controlled original driver FX combinations")
    # Independent field extraction negative mutations: first write per active
    # voice is required; voice26 sample upload must NEVER count as an audio voice.
    good=[(2,"PSST_LO",100),(2,"PTRX_LO",0x7F20),(2,"CSL_HI",0x4020)]
    s=original_sends(good)
    require(s["reverb_first_by_voice"]=={"2":127} and
            s["chorus_first_by_voice"]=={"2":64},
            "extract genuine full 8-bit send bytes, not low-byte garbage")
    for damaged in (
        [(26,"PSST_LO",100),(26,"PTRX_LO",0x7F20),(26,"CSL_HI",0x4020)],
        [(2,"PSST_LO",100),(2,"PTRX_HI",0x7F20),(2,"CSL_HI",0x4020)],
        [(2,"PSST_LO",100),(2,"PTRX_LO",0x7F20),(2,"CSL_LO",0x4020)],
        [(3,"PSST_LO",100),(2,"PTRX_LO",0x7F20),(2,"CSL_HI",0x4020)],
    ):
        try:original_sends(damaged)
        except ValueError:continue
        raise AssertionError("P227 accepted a false original note-register oracle")
    print("P227_MATRIX_AND_FOUR_NEGATIVE_SEND_ORACLES_PASS")

def run(conn,out,trace,fifo,send,screenshot,report,pcm_fifo):
    test_matrix()
    require(report.get("hardware")=="sbawe64_gold" and
            report.get("sample_ram_kib")==28672 and
            report.get("p75_private_sample_upload_plausible") and
            report.get("p75_private_sample_upload_write_words",0)>=
                report.get("p75_private_sample_upload_minimum_words",10**30),
            "source bank not demonstrably uploaded into original Creative 28MiB RAM")
    require(report.get("p84_universal_sf2_test"),
            "test bank not loaded via original Creative AWECP Win95")
    require(trace.is_file(),"missing real P45 original 86Box I/O capture")
    send(conn,"step 2000")
    screenshot(conn,out,"p227-original-creative-agent-active.png",report)
    fd=connect_linux_86box_fifo(fifo)
    tap=PcmReceiver(pcm_fifo) if pcm_fifo else None
    if tap:tap.start()
    before=counts(trace)
    cases=[]
    uart_messages=0
    pcm_summary=None
    try:
        for case in matrix():
            # Reset note state between trials; all other MIDI/driver settings
            # are identical except stage CC91 / CC93 and note velocity.
            ccs=((0,BANK),(7,100),(11,127),(1,96),
                 (91,case["cc91"]),(93,case["cc93"]))
            for cc,value in ccs:
                send_paced_frame(fd,frame(0xB0|CHANNEL,cc,value),conn,send)
                uart_messages+=1
            send_paced_frame(fd,frame(0xC0|CHANNEL,case["program"]),conn,send)
            uart_messages+=1
            send(conn,"step 300")
            case_dir=out/"p227-PRIVATE-windows-wavetable"/case["id"]
            case_dir.mkdir(parents=True,exist_ok=False)
            require(not list(case_dir.iterdir()),"stale per-case original WAV")
            start=counts(trace)
            require(start>=before,"I/O trace reset / nonmonotonic original capture")
            started=False
            try:
                send(conn,f"audio start {case_dir.resolve()}")
                started=True
                send(conn,"step 50")
                send_paced_frame(fd,frame(0x90|CHANNEL,NOTE,case["velocity"]),conn,send)
                uart_messages+=1
                send(conn,"step 1000")
                send_paced_frame(fd,frame(0x80|CHANNEL,NOTE,0),conn,send)
                uart_messages+=1
                send(conn,"step 2000")
            finally:
                if started:send(conn,"audio stop")
            end=counts(trace)
            require(end>start,"original driver wrote no registers for "+case["id"])
            regs=original_csv(trace,start,end)
            sends=original_sends(regs)
            paths=[p for p in case_dir.glob("*.wav") if "wavetable" in p.name.lower()]
            require(len(paths)==1,"one and only one original Win95 wavetable capture "+case["id"])
            audio=pcm_statistics(paths[0])
            cases.append({**case,**sends,"source":"original_Win95_Creative_WinMM",
                          "register_write_count":len(regs),
                          "start_row":start,"end_row":end,
                          "original_86box_wavetable_audio":audio})
            print("P227_REAL_CREATIVE",case["id"],
                  "PTRX_REV=",sends["reverb_first_by_voice"],
                  "CSL_CHOR=",sends["chorus_first_by_voice"],
                  "rms=",audio["rms"],flush=True)
        require(len(cases)==16,"not all original Win95 trials executed")
    finally:
        os.close(fd)
        if tap:pcm_summary=tap.stop()
    require(pcm_summary is not None and pcm_summary.get("nonzero_frames",0)>0,
            "real 86Box wavetable FIFO did not emit audible original driver PCM")
    result=dict(
        p227_original_win95_creative_fx=True,
        note=NOTE,programs=list(PROGRAMS),
        original_creative_midi_activity_register_write_delta=counts(trace)-before,
        p89_original_first_note_trace_window=cases[0],
        p75_original_private_sf2_test=False, # public source media only
        p75_program_results=[],
        p74_uart_frames_injected=uart_messages,
        original_creative_wavetable_audio=None,
        direct_86box_pcm_fifo=pcm_summary,
        p227_original_fx_cases=cases,
        raw_private_audio_published=False,
        notes="Real Win95 SBAWE original endpoint; 86Box wavetable output; public authenticated SF2, NOT owner bank, NOT physical AWE64")
    require(result["original_creative_midi_activity_register_write_delta"]>0,
            "no authentic Creative MIDI/IO register activity")
    report["p64_original_win95_midi"]=result
    return result

if __name__=="__main__":
    test_matrix()
