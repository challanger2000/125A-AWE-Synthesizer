#!/usr/bin/env python3
"""P87: record six D4 audition notes through REAL Win95/Creative WinMM and 86Box.

Uses the original Creative MIDI endpoint and 86Box's wavetable PCM output;
never injects EMU8000 register values or synthesizes replacement samples.
The private user SoundFont must already be loaded through the original
AWE Control Panel. Requires external P67 guest log verification afterwards.
"""
from __future__ import annotations
import os
import shutil
from pathlib import Path
from p63_send_guest_midi import frame,demo_messages
from p64_original_win95_midi_trial import connect_linux_86box_fifo,send_paced_frame
from p76_export_private_wav import pcm_stats

D4_AUDITIONS=(
    (0,36,"StandardStuff-Kick"),(0,38,"StandardStuff-Snare"),
    (0,42,"StandardStuff-HiHat"),(17,36,"Industrial-Kick"),
    (17,38,"Industrial-Snare"),(17,42,"Industrial-HiHat"))

def capture_six(conn,send,midi_fifo,report,output_dir,private_dir,
                auditions=D4_AUDITIONS,bank_select=1,channel=0):
    if not report.get("p84_universal_sf2_test"):
        raise ValueError("P87 requires universal original Creative SF2 mode")
    if not report.get("p75_private_sample_upload_plausible"):
        raise ValueError("Original Creative SF2 sample RAM upload not proven")
    if report.get("hardware")!="sbawe64_gold" or report.get("sample_ram_kib")!=28672:
        raise ValueError("P87 needs verified 28MiB AWE64 Gold configuration")
    if not 0<=bank_select<=127 or not 0<=channel<=15:
        raise ValueError("Invalid Win95 MIDI bank or channel")
    if not auditions or len(set((p,n) for p,n,_ in auditions))!=len(auditions):
        raise ValueError("P87 requires unique program/note combinations")
    for p,n,_ in auditions:
        if not 0<=p<=127 or not 0<=n<=127:
            raise ValueError("Invalid P87 program/note")
    output_dir=Path(output_dir)
    private_dir=Path(private_dir)
    captured=[]
    # Only one 86Box COM FIFO writer per audition; send one UART byte per
    # emulated time slice to avoid overflowing the Win95 8250 serial port.
    fd=connect_linux_86box_fifo(Path(midi_fifo))
    try:
        for p,n,name in auditions:
            for msg in demo_messages(channel=channel,bank=bank_select,
                                     program=p,note=n,velocity=100):
                send_paced_frame(fd,msg,conn,send)
            send(conn,"step 400")
            dest=output_dir/f"P{p}-N{n}"
            dest.mkdir(parents=True,exist_ok=True)
            recording=False
            try:
                send(conn,f"audio start {dest.resolve()}")
                recording=True
                send_paced_frame(fd,frame(0x90|channel,n,100),conn,send)
                send(conn,"step 2000")
                send_paced_frame(fd,frame(0x80|channel,n,0),conn,send)
                send(conn,"step 400")
            finally:
                if recording:send(conn,"audio stop")
            wav=[x for x in dest.glob("*.wav") if "wavetable" in x.name.lower()]
            if len(wav)!=1:
                raise RuntimeError(f"Program {p} note {n}: no unique 86Box wavetable capture")
            metrics=pcm_stats(wav[0])
            captured.append({"program":p,"note":n,"name":name,
                             "source_wav":wav[0],"audio":metrics})
    finally:
        os.close(fd)
    # Only copy the six original Creative WAVs AFTER all six are validated.
    private_dir.mkdir(parents=True,exist_ok=True)
    files=[]
    for item in captured:
        path=private_dir/f"P{item['program']}-N{item['note']}-{item['name']}-Original-Win95-Creative.wav"
        shutil.copyfile(item["source_wav"],path)
        if path.stat().st_size!=item["source_wav"].stat().st_size:
            raise IOError("Truncated original Win95 Creative WAV")
        files.append({"program":item["program"],"note":item["note"],
                      "name":item["name"],"audio":item["audio"],
                      "file":str(path)})
    result={"phase":"P87","source_backend":"original Win95 Creative WinMM AWE64 Gold",
            "emu8000":True,"auditions":files,"validated_wavs":len(files),
            "actual_original_win95_guest_p67_still_required":True,
            "physical_hardware_parity_proven":False}
    report["p87_original_win95_six_notes"]=result
    return result
