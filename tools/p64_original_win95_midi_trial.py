#!/usr/bin/env python3
"""Exercise original Creative Win95 MIDI through actual 86Box serial I/O.

P64 uses real Win95 guest MIDI agent (P63), original Creative AWECP32-loaded
SF2 and emulated 86Box EMU8000; does NOT inject fake registers or use P26 DSP.
"""
import errno
import os
import time
from pathlib import Path
from p63_send_guest_midi import frame, demo_messages
from p58_analyze_audio import analyze_wav
from p65_pcm_receiver import PcmReceiver


def connect_linux_86box_fifo(base: Path, timeout_s=12):
    """86Box pipe server .in is guest RX; write there, never .out."""
    path = Path(str(base)+".in")
    deadline = time.monotonic()+timeout_s
    while time.monotonic()<deadline:
        try:
            return os.open(path,os.O_WRONLY|os.O_NONBLOCK)
        except OSError as exc:
            if exc.errno not in (errno.ENOENT,errno.ENXIO,errno.EAGAIN):
                raise
            time.sleep(.15)
    raise TimeoutError("86Box COM1 FIFO reader not connected")


def run_trial(conn, out: Path, trace: Path, fifo_base: Path,
              send, key, type_path, screenshot, report, pcm_fifo=None):
    # AWE Control Panel has already selected and applied the original SF2.
    # Do not reimplement SF2 loading in our guest agent.
    send(conn,"key down 0x38 0x3e")  # Alt+F4 closes original Control Panel
    send(conn,"key up 0x3e 0x38")
    send(conn,"step 600")
    send(conn,"key down 0x1d 0x01")  # Ctrl+Esc, Start
    send(conn,"key up 0x01 0x1d")
    send(conn,"step 250")
    key(conn,0x13)                  # Run...
    send(conn,"step 500")
    type_path(conn,r"c:\awe32\p63midi.exe")
    # Win95 consumes injected scan codes asynchronously. P67 screenshot
    # showed only \"...p63midi.e\" before Return, so execution never started.
    # Step guest CPU to flush ALL pending keystrokes before pressing Enter.
    send(conn,"step 1500")
    screenshot(conn,out,"p64-agent-start-command.png",report)
    key(conn,0x1c)
    send(conn,"step 5500")
    screenshot(conn,out,"p64-agent-started.png",report)

    count_before = max(0,len(trace.read_text(encoding="utf8", errors="replace").splitlines())-1) if trace.is_file() else 0
    fd=connect_linux_86box_fifo(fifo_base)
    pcm_receiver=PcmReceiver(pcm_fifo) if pcm_fifo else None
    if pcm_receiver:pcm_receiver.start()
    audio_dir=out/"p64-private-original-creative-wavetable"
    audio_dir.mkdir(exist_ok=True)
    try:
        init=tuple(demo_messages(channel=0,bank=1,program=0,note=48,velocity=100))
        for msg in init:
            os.write(fd,msg)
        send(conn,"step 400")
        # Recording starts before the real original Creative note is sent.
        audio_started=False
        try:
            send(conn,f"audio start {audio_dir.resolve()}")
            audio_started=True
        except Exception as exc:
            report["p64_audio_start_error"]=str(exc)
        os.write(fd,frame(0x90,48,100))
        send(conn,"step 1200")
        screenshot(conn,out,"p64-creative-playing.png",report)
        os.write(fd,frame(0x80,48,0))
        send(conn,"step 1200")
        if audio_started:
            send(conn,"audio stop")
    finally:
        os.close(fd)
    count_after=max(0,len(trace.read_text(encoding="utf8", errors="replace").splitlines())-1) if trace.is_file() else count_before
    wav_files=sorted(audio_dir.rglob("*wav"))
    wavetable=[p for p in wav_files if "wavetable" in p.name.lower()]
    analysis=None
    if wavetable:
        try:
            analysis=analyze_wav(wavetable[0],note=48)
        except Exception as exc:
            analysis={"analysis_error":str(exc)}
    pcm_report=pcm_receiver.stop() if pcm_receiver else None
    result={"guest_agent_executed_by_win95_run_command":True,
            "original_creative_midi_endpoint_verified":False,
            "original_creative_midi_activity_register_write_delta":max(0,count_after-count_before),
            "original_creative_wavetable_audio":analysis,
            "direct_86box_pcm_fifo":pcm_report,
            "private_wavetable_file_found":bool(wavetable),
            "raw_private_audio_published":False,
            "sf2_fixture":"original generated P55 SF2 in Creative User Bank1",
            "notes":"A screenshot verifies the actual guest process, register activity and audio must separately confirm MIDI route"}
    report["p64_original_win95_midi"]=result
    return result
