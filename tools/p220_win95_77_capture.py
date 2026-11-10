#!/usr/bin/env python3
"""P220 private ORIGINAL Creative Win95 77-program 86Box PCM capture stage.

Reuses existing P48/P63/P64/P75/P80/P87: original loaded control panel,
WinMM AWE Synth selected in Win95, byte-paced COM1 MIDI, EMU8000 wavetable
PCM from 86Box automation; no new virtual machine or synthesizer.

This is only the capture stage. An independent P67 guest-log/driver audit
AFTER the VM closes is mandatory before creating an ORIGINAL provenance
claim. No raw SoundFont, 86Box ROM, private WAVs or guest images to GitHub.
"""
from __future__ import annotations
import hashlib,json,os,shutil
from pathlib import Path
from p63_send_guest_midi import frame
from p64_original_win95_midi_trial import connect_linux_86box_fifo,send_paced_frame
from p76_export_private_wav import pcm_stats
from p89_compare_voice_registers import original_csv
from p220_77_preset_capture_plan import BANK_SHA,SCHEMA,plan as generate_plan

def require(ok,msg):
    if not ok:raise ValueError("P220 ORIGINAL WIN95 CAPTURE ABORTED: "+msg)

def validate(source_sf2,planned,report):
    # Validate all 77 source-preset names, MIDI mapping and numeric events
    # against the original bytes, not against our target VST3's browser.
    expected=generate_plan(source_sf2)
    keys=("schema","private_sf2_sha256","presets","programs","scenarios","missing_midi_program")
    require(all(planned.get(k)==expected[k] for k in keys),
            "independent immutable 77-preset SF2/MIDI plan differs from private source")
    require(planned["schema"]==SCHEMA and planned["private_sf2_sha256"]==BANK_SHA,
            "private original bank SHA mismatch")
    require(report.get("hardware")=="sbawe64_gold" and
            report.get("sample_ram_kib")==28672 and
            report.get("full_77_preset_soundfont_validated") is True and
            report.get("p75_private_sample_upload_plausible") is True and
            type(report.get("p75_private_sample_upload_write_words")) is int and
            report["p75_private_sample_upload_write_words"]>=
                report.get("p75_private_sample_upload_minimum_words",2**40),
            "only inventory or incomplete Creative SF2 DRAM upload; cannot play")
    return expected["scenarios"]

def rows_before(path):
    if not Path(path).is_file():return -1
    # CSV row offsets MUST count actual parser rows rather than raw bytes
    # because P89 original_csv validates row range in 0-based data rows.
    with Path(path).open("r",encoding="utf8",errors="replace") as f:
        return max(-1,sum(1 for _ in f)-1)

def run(conn,send,midi_fifo,trace,report,private_sf2,planned,raw_output,private_output):
    cases=validate(private_sf2,planned,report)
    raw_output=Path(raw_output)
    private_output=Path(private_output)
    raw_output.mkdir(parents=True,exist_ok=True)
    private_output.mkdir(parents=True,exist_ok=True)
    require(raw_output.resolve()!=private_output.resolve(),
            "private archive must not share raw working directory")
    fd=connect_linux_86box_fifo(Path(midi_fifo))
    results=[]
    total_frames=0
    try:
        for case in cases:
            label=case["id"]
            channel=case["channel"];p=case["program"]
            # Explicit every-case CC reset prevents history, reverb, sustain,
            # bank and mod-wheel state leaking between independent auditions.
            event_data=[(0xB0|channel,0,case["user_bank"])]
            for cc in (7,11,1,91,93):
                event_data.append((0xB0|channel,cc,case["controllers"][str(cc)]))
            event_data.append((0xC0|channel,p,0))
            require(len(event_data)==7,"incorrect new midi event schedule")
            for status,a,b in event_data:
                send_paced_frame(fd,frame(status,a,b),conn,send)
            send(conn,"step 260") # allow original guest WinMM program settle
            directory=raw_output/label
            directory.mkdir(parents=True,exist_ok=True)
            require(not list(directory.glob("*.wav")),
                    "stale PCM file present for "+label)
            original_start=rows_before(trace)
            recording=False
            try:
                send(conn,f"audio start {directory.resolve()}")
                recording=True
                send(conn,"step 50")
                send_paced_frame(fd,frame(0x90|channel,case["note"],case["velocity"]),conn,send)
                send(conn,"step 1000")
                send_paced_frame(fd,frame(0x80|channel,case["note"],0),conn,send)
                send(conn,"step 2000")
            finally:
                if recording:send(conn,"audio stop")
            original_end=rows_before(trace)
            require(original_end>original_start>=0,
                    "no actual original driver I/O note window for "+label)
            regs=original_csv(trace,original_start,original_end)
            note_registers=[(v,n,val) for v,n,val in regs if n in (
                "PSST_LO","PSST_HI","CSL_LO","CSL_HI",
                "CCCA_LO","CCCA_HI","IFATN","IP")]
            has_sample_start=any(n in ("PSST_LO","PSST_HI") for _,n,_ in note_registers)
            require(has_sample_start and len({v for v,_,_ in regs})>=1,
                    "no original AWE sample-start/voice register writes for "+label)
            captures=[x for x in directory.glob("*.wav") if "wavetable" in x.name.lower()]
            require(len(captures)==1,"not exactly one original 86Box wavetable WAV "+label)
            info=pcm_stats(captures[0])
            expected_frames=case["record_ms"]*44100//1000
            require(abs(info["frames"]-expected_frames)<=44100//5,
                    "actual original audio length incompatible with MIDI timeline "+label)
            dest=private_output/(label+".wav")
            require(not dest.exists(),"cannot overwrite pre-existing private capture "+label)
            shutil.copyfile(captures[0],dest)
            require(dest.stat().st_size==captures[0].stat().st_size,
                    "private original audio copy truncated")
            item={"id":label,"program":p,"note":case["note"],
                  "velocity":case["velocity"],"controllers":case["controllers"],
                  "note_off_observed":"PENDING_GUEST_WINMM_ACK",
                  "note_off_sent_to_guest":True,
                  "audio_frames":info["frames"],
                  "wav_sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
                  "creative_program_change_delivered":"PENDING_P67_WINMM_GUEST_LOG",
                  "original_emu8000_voice_write_delta":len(regs),
                  "sf2_bank_program_selected":p,
                  "original_sample_start_register_written":has_sample_start,
                  "source_audio_pcm_from":"86box_wavetable_during_real_original_Win95",
                  "original_capture_csv_bounds":[original_start,original_end],
                  "physical_AWE64":False,
                  "private_wav_exported_to_public_GitHub":False}
            results.append(item)
            total_frames+=info["frames"]
    finally:
        os.close(fd)
    require(len(results)==154 and
            [(x["id"],x["program"]) for x in results]==
            [(x["id"],x["program"]) for x in cases],
            "not all 154 original Creative notes actually tested")
    report["p220_original_win95_private_capture"]={
        "schema":"125a-p220-creative-win95-pending-after-guest-verification-v1",
        "private_sf2_sha256":BANK_SHA,"trials":results,
        "all_154_original_pcm_captured":True,
        "actual_wavetable_frames":total_frames,
        "original_Guest_P67_log_verification":"NOT RUN",
        "sample_RAM_specific_readback":"NOT RUN",
        "real_hardware_AWE64":"NOT RUN",
        "release_approved":False}
    return report["p220_original_win95_private_capture"]
