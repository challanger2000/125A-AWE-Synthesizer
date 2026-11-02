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


def send_paced_frame(fd, payload: bytes, conn, send, pace_ms=25):
    """Transmit one UART character per guest-emulated timeslice.

    Injecting 6 bytes in a single Linux write floods an emulated 8250 UART
    which has no receiving FIFO in original Windows 95 configurations.
    Each 25ms guest step lets the actual Windows COM1 ISR/service thread
    consume a byte before the following one arrives. The guest WinMM code
    still processes all MIDI messages, not a replacement synth.
    """
    if not payload:
        raise ValueError("Cannot transmit empty COM1 frame")
    for value in payload:
        count = os.write(fd, bytes((value,)))
        if count != 1:
            raise IOError(f"Short COM1 UART write: {count}")
        send(conn, f"step {pace_ms}")
    return len(payload)


def run_trial(conn, out: Path, trace: Path, fifo_base: Path,
              send, key, type_path, screenshot, report, pcm_fifo=None, programs=(0,)):
    # P68 WIN.INI run= launched the CRT-free original Creative MIDI agent
    # at Windows 95 startup. Do not try to type the command into Run again:
    # those keystrokes were reliably accepted but failed to start the EXE.
    send(conn, "step 2000")
    screenshot(conn, out, "p68-agent-autostart-state.png", report)

    count_before = max(0,len(trace.read_text(encoding="utf8", errors="replace").splitlines())-1) if trace.is_file() else 0
    fd=connect_linux_86box_fifo(fifo_base)
    pcm_receiver=PcmReceiver(pcm_fifo) if pcm_fifo else None
    if pcm_receiver:pcm_receiver.start()
    audio_dir=out/"p64-private-original-creative-wavetable"
    other_dir=out/"p75-private-program7"
    uart_bytes_sent=0
    uart_frames_sent=0
    audio_dir.mkdir(exist_ok=True)
    try:
        init=tuple(demo_messages(channel=0,bank=1,program=0,note=48,velocity=100))
        for msg in init:
            uart_bytes_sent+=send_paced_frame(fd,msg,conn,send)
            uart_frames_sent+=1
        send(conn,"step 400")
        # Recording starts before the real original Creative note is sent.
        audio_started=False
        try:
            send(conn,f"audio start {audio_dir.resolve()}")
            audio_started=True
        except Exception as exc:
            report["p64_audio_start_error"]=str(exc)
        uart_bytes_sent+=send_paced_frame(fd,frame(0x90,48,100),conn,send)
        uart_frames_sent+=1
        send(conn,"step 1200")
        screenshot(conn,out,"p64-creative-playing.png",report)
        uart_bytes_sent+=send_paced_frame(fd,frame(0x80,48,0),conn,send)
        uart_frames_sent+=1
        send(conn,"step 1200")
        if audio_started:
            send(conn,"audio stop")
        p75_program7_before=max(0,len(trace.read_text(encoding="utf8",errors="replace").splitlines())-1) if trace.is_file() else 0
        if 7 in programs:
            other_dir.mkdir(exist_ok=True)
            for msg in demo_messages(channel=0,bank=1,program=7,note=48,velocity=100):
                send_paced_frame(fd,msg,conn,send)
            send(conn,"step 400")
            p75_recording=False
            try:
                send(conn,f"audio start {other_dir.resolve()}")
                p75_recording=True
            except Exception as exc:
                report["p75_recording_error"]=str(exc)
            send_paced_frame(fd,frame(0x90,48,100),conn,send)
            send(conn,"step 1200")
            screenshot(conn,out,"p75-program7-playing.png",report)
            send_paced_frame(fd,frame(0x80,48,0),conn,send)
            send(conn,"step 1200")
            if p75_recording:
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
    p75_program_reports=[]
    if 7 in programs:
        second=[p for p in sorted(other_dir.rglob("*.wav")) if "wavetable" in p.name.lower()]
        analysis7=None
        if second:
            try:
                analysis7=analyze_wav(second[0],note=48)
            except Exception as exc:
                analysis7={"analysis_error":str(exc)}
        p75_program_reports=[
            {"program":0,"name":"Grungy Ramp Bass","bank_select_cc0":1,
             "wavetable_statistics":analysis,
             "nonzero_audio":bool(analysis and analysis.get("window_rms_dbfs",-300)>-299),
             "raw_audio_uploaded":False},
            {"program":7,"name":"TX81Z Lately Bass","bank_select_cc0":1,
             "wavetable_statistics":analysis7,
             "nonzero_audio":bool(analysis7 and analysis7.get("window_rms_dbfs",-300)>-299),
             "register_write_delta":max(0,count_after-p75_program7_before),
             "raw_audio_uploaded":False}]
    result={"p75_original_private_sf2_test":7 in programs,
            "p75_program_results":p75_program_reports,
            "p74_uart_bytes_injected":uart_bytes_sent,
            "p74_uart_frames_injected":uart_frames_sent,
            "p74_uart_guest_step_per_byte_ms":25,
            "p74_uart_com1_received_confirmed":False,
            "guest_agent_executed_by_win95_run_command":False,
            "guest_agent_autostart_requested":True,
            "original_creative_midi_endpoint_verified":False,
            "original_creative_midi_activity_register_write_delta":max(0,count_after-count_before),
            "original_creative_wavetable_audio":analysis,
            "direct_86box_pcm_fifo":pcm_report,
            "private_wavetable_file_found":bool(wavetable),
            "raw_private_audio_published":False,
            "sf2_fixture":"local private original SF2" if 7 in programs else "original generated P55 SF2 in Creative User Bank1",
            "notes":"A screenshot verifies the actual guest process, register activity and audio must separately confirm MIDI route"}
    report["p64_original_win95_midi"]=result
    return result
