#!/usr/bin/env python3
"""P230: controlled original Creative Win95/86Box GM ROM acoustic pilot.
Requires an *already running* original Win95/Creative WinMM/P64 guest.
No waveforms, driver or ROM are bundled; original provenance is checked
separately after the guest shuts down using P67.
"""
from __future__ import annotations
import hashlib
import os
import shutil
from pathlib import Path
from p63_send_guest_midi import frame
from p64_original_win95_midi_trial import connect_linux_86box_fifo, send_paced_frame
from p76_export_private_wav import pcm_stats
from p89_compare_voice_registers import original_csv

# Each of these 8 cases is a subset of native P230's full 397 matrix.
MELODIC=(0,39,80,88,112)
DRUMS=(36,38,42)

def plan():
    return tuple((16383,p,60,100,0) for p in MELODIC)+tuple(
        (16382,0,n,100,9) for n in DRUMS)

def label(bank,program,note,velocity):
    prefix="gm" if bank==16383 else "drum"
    return f"{prefix}_b{bank:05}_p{program:03}_n{note:03}_v{velocity:03}.wav"

def controllers(channel):
    # Creative channel 10 has an implicit original GM drum kit. CC0=0
    # explicitly switches banks and may remove the drum routing.
    baseline=((7,100),(11,127),(10,64),(1,0),(64,0),(91,0),(93,0))
    return baseline if channel==9 else ((0,0),)+baseline

def self_test():
    cases=plan()
    assert len(cases)==8
    assert all(bank in (16382,16383) for bank,_,_,_,_ in cases)
    assert all((channel==9)==(bank==16382) for bank,_,_,_,channel in cases)
    assert len({label(b,p,n,v) for b,p,n,v,_ in cases})==8
    assert set(MELODIC)<set(range(128)) and set(DRUMS)<set(range(128))
    assert (0,0) in controllers(0) and all(cc!=0 for cc,_ in controllers(9))
    print("P230_CREATIVE_GM_8_CASE_ORIGINAL_GUEST_PLAN_PASS")

def row_index(path):
    if not Path(path).is_file():return -1
    with Path(path).open("r",encoding="utf8",errors="replace") as f:
        return max(-1,sum(1 for _ in f)-1)

def capture(conn,send,guest_fifo,trace,report,raw_dir,private_dir):
    self_test()
    if report.get("hardware")!="sbawe64_gold" or report.get("sample_ram_kib")!=28672:
        raise ValueError("P230 requires original Creative Win95 AWE64 Gold guest")
    if report.get("private_sf2_supplied"):
        raise ValueError("P230 original ROM test must not load an owner SF2")
    if not report.get("p64_original_win95_midi",{}).get(
            "original_creative_midi_activity_register_write_delta",0)>0:
        raise ValueError("P230 original WinMM/P64 bridge not proven active")
    raw_dir=Path(raw_dir);private_dir=Path(private_dir)
    if raw_dir.resolve()==private_dir.resolve():
        raise ValueError("P230 cannot share raw and archive paths")
    if private_dir.exists():
        raise ValueError("P230 refuses to overwrite original references")
    raw_dir.mkdir(parents=True,exist_ok=False)
    private_dir.mkdir(parents=True,exist_ok=False)
    fd=connect_linux_86box_fifo(Path(guest_fifo))
    records=[]
    try:
        for bank,program,note,velocity,channel in plan():
            fname=label(bank,program,note,velocity)
            guest_bank=0  # Original Win95 Creative 1MGM program bank
            # Channel 10 selects the original GM percussion map.
            reset=controllers(channel)
            for cc,val in reset:
                send_paced_frame(fd,frame(0xB0|channel,cc,val),conn,send)
            send_paced_frame(fd,frame(0xC0|channel,program,0),conn,send)
            send(conn,"step 260")
            before=row_index(trace)
            folder=raw_dir/fname.removesuffix(".wav")
            folder.mkdir()
            started=False
            try:
                send(conn,f"audio start {folder.resolve()}")
                started=True
                send(conn,"step 50")
                send_paced_frame(fd,frame(0x90|channel,note,velocity),conn,send)
                send(conn,"step 1000")
                send_paced_frame(fd,frame(0x80|channel,note,0),conn,send)
                send(conn,"step 1000")
            finally:
                if started:send(conn,"audio stop")
            after=row_index(trace)
            if before<0 or after<=before:
                raise RuntimeError("No original Creative EMU8000 note I/O for "+fname)
            registers=original_csv(trace,before,after)
            if not any(register in ("PSST_LO","PSST_HI","CCCA_LO","CCCA_HI")
                       for _,register,_ in registers):
                raise RuntimeError("No Creative sample pointer writes for "+fname)
            found=[p for p in folder.glob("*.wav") if "wavetable" in p.name.lower()]
            if len(found)!=1:
                raise RuntimeError("Original 86Box wavetable capture missing/ambiguous "+fname)
            pcm=pcm_stats(found[0])
            good=(80000<=pcm["frames"]<=105000 and pcm["nonzero_frames"]>=(100 if channel==9 else 1000))
            if not good and channel!=9:
                raise RuntimeError("Original melodic ROM audio invalid "+fname+
                                   " "+str(pcm))
            target=private_dir/fname
            shutil.copyfile(found[0],target)
            records.append({"file":fname,"bank":bank,"program":program,
                            "valid_original_pcm":good,
                            "pcm_observed":pcm,
                            "note":note,"velocity":velocity,"channel":channel,
                            "guest_bank_cc0":(guest_bank if channel!=9 else "not_sent_implicit_original_drum"),
                            "source":"booted_Win95_Creative_WinMM",
                            "source_audio":"86Box_original_wavetable_tap",
                            "creative_register_window":[before,after],
                            "register_entries":len(registers),
                            "register_write_sequence":registers,
                            "audio_frames":pcm["frames"],
                            "reference_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
                            "guest_delivery_ack":"P67_REQUIRED_AFTER_GUEST"})
    finally:
        os.close(fd)
    report["p230_original_gm_8_capture"]={
        "cases":records,"reference_count":len(records),
        "valid_pcm_count":sum(bool(x["valid_original_pcm"]) for x in records),
        "invalid_pcm_cases":[x for x in records if not x["valid_original_pcm"]],
        "creative_driver_live_registers":all(x["register_entries"]>0 for x in records),
        "P67_guest_original_driver_provenance":"NOT_RUN",
        "full_397_original_reference":"NOT_RUN",
        "physical_AWE64":"NOT_RUN"}
    return report["p230_original_gm_8_capture"]

if __name__=="__main__":
    self_test()
