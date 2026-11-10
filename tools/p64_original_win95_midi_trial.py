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
              send, key, type_path, screenshot, report, pcm_fifo=None, programs=(0,), note=48, creative_bank=1, preset_names=None, midi_channel=0, p210_sweep=False, p212_sweep=False, p214_sweep=False, p217_sweep=False):
    if p210_sweep or p212_sweep or p214_sweep or p217_sweep:
        return run_p210_real_driver_sweep(conn,out,trace,fifo_base,send,
                                         screenshot,report,pcm_fifo,programs,
                                         note,creative_bank,midi_channel,p212_sweep=p212_sweep,
                                          p214_sweep=p214_sweep, p217_sweep=p217_sweep)
    if not programs or len(programs)>2 or any(not 0<=v<=127 for v in programs):
        raise ValueError("Select one or two valid MIDI program numbers")
    if not 0<=note<=127 or not 0<=creative_bank<=127 or not 0<=midi_channel<=15:
        raise ValueError("Invalid MIDI note, Creative user bank or channel")
    first_program=programs[0]
    second_program=programs[1] if len(programs)==2 else None
    names=preset_names or {}
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
        init=tuple(demo_messages(channel=midi_channel,bank=creative_bank,program=first_program,note=note,velocity=100))
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
        # P89: an isolated original Creative port-write window for one
        # known program/note. Start AFTER all bank/CC/program messages and
        # AFTER the complete SF2 upload; end BEFORE changing program again.
        p89_first_start=max(0,len(trace.read_text(encoding="utf8",errors="replace").splitlines())-1) if trace.is_file() else -1
        uart_bytes_sent+=send_paced_frame(fd,frame(0x90|midi_channel,note,100),conn,send)
        uart_frames_sent+=1
        send(conn,"step 1200")
        screenshot(conn,out,"p64-creative-playing.png",report)
        uart_bytes_sent+=send_paced_frame(fd,frame(0x80|midi_channel,note,0),conn,send)
        uart_frames_sent+=1
        send(conn,"step 1200")
        if audio_started:
            send(conn,"audio stop")
        p89_first_end=max(0,len(trace.read_text(encoding="utf8",errors="replace").splitlines())-1) if trace.is_file() else -1
        p75_program7_before=max(0,len(trace.read_text(encoding="utf8",errors="replace").splitlines())-1) if trace.is_file() else 0
        if second_program is not None:
            other_dir.mkdir(exist_ok=True)
            for msg in demo_messages(channel=midi_channel,bank=creative_bank,program=second_program,note=note,velocity=100):
                send_paced_frame(fd,msg,conn,send)
            send(conn,"step 400")
            p75_recording=False
            try:
                send(conn,f"audio start {other_dir.resolve()}")
                p75_recording=True
            except Exception as exc:
                report["p75_recording_error"]=str(exc)
            send_paced_frame(fd,frame(0x90|midi_channel,note,100),conn,send)
            send(conn,"step 1200")
            screenshot(conn,out,"p75-program7-playing.png",report)
            send_paced_frame(fd,frame(0x80|midi_channel,note,0),conn,send)
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
            analysis=analyze_wav(wavetable[0],note=note)
        except Exception as exc:
            analysis={"analysis_error":str(exc)}
    pcm_report=pcm_receiver.stop() if pcm_receiver else None
    p75_program_reports=[]
    if second_program is not None:
        second=[p for p in sorted(other_dir.rglob("*.wav")) if "wavetable" in p.name.lower()]
        analysis7=None
        if second:
            try:
                analysis7=analyze_wav(second[0],note=note)
            except Exception as exc:
                analysis7={"analysis_error":str(exc)}
        p75_program_reports=[
            {"program":first_program,"name":names.get(first_program,"Preset "+str(first_program)),"bank_select_cc0":creative_bank,
             "wavetable_statistics":analysis,
             "nonzero_audio":bool(analysis and analysis.get("window_rms_dbfs",-300)>-299),
             "raw_audio_uploaded":False},
            {"program":second_program,"name":names.get(second_program,"Preset "+str(second_program)),"bank_select_cc0":creative_bank,
             "wavetable_statistics":analysis7,
             "nonzero_audio":bool(analysis7 and analysis7.get("window_rms_dbfs",-300)>-299),
             "register_write_delta":max(0,count_after-p75_program7_before),
             "raw_audio_uploaded":False}]
    result={"p89_original_first_note_trace_window":{
                "program":first_program,"note":note,"velocity":100,
                "start_row":p89_first_start,"end_row":p89_first_end,
                "window_isolated":p89_first_end>p89_first_start>=0},
            "p84_midi_channel_0_based":midi_channel,
            "p75_original_private_sf2_test":second_program is not None,
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
            "sf2_fixture":"local private original SF2" if second_program is not None else "original generated P55 SF2 in Creative User Bank1",
            "notes":"A screenshot verifies the actual guest process, register activity and audio must separately confirm MIDI route"}
    report["p64_original_win95_midi"]=result
    return result


def run_p210_real_driver_sweep(conn, out, trace, fifo_base, send,
                               screenshot, report, pcm_fifo, programs,
                               note, creative_bank, midi_channel, p212_sweep=False, p214_sweep=False, p217_sweep=False):
    """RESEARCH ONLY. Play 14/28 distinct generated SF2 presets through the
    actual Win95 guest Creative WinMM endpoint with 86Box EMU8000 I/O tap.
    This never synthesizes MIDI on the host and never writes EMU registers.
    A separate CSV window is frozen for every note, not just the first.
    """
    expected_count=28 if (p212_sweep or p214_sweep or p217_sweep) else 14
    if (len(programs)!=expected_count or len(set(programs))!=expected_count or note!=59
            or midi_channel!=0 or creative_bank!=1):
        raise ValueError("P210 exact controlled note59 bank1 14-program sweep required")
    from p63_send_guest_midi import frame, demo_messages
    send(conn,"step 2000")
    screenshot(conn,out,"p210-creative-guest-autostart.png",report)
    def rowcount():
        return max(0,len(trace.read_text(encoding="utf8",errors="replace").splitlines())-1) if trace.is_file() else -1
    before=rowcount()
    if before < 0:
        raise RuntimeError("P210 missing authentic 86Box EMU8000 port-trace instrument")
    fd=connect_linux_86box_fifo(fifo_base)
    pcm=PcmReceiver(pcm_fifo) if pcm_fifo else None
    if pcm:pcm.start()
    windows=[]
    uart_frames=0
    uart_bytes=0
    pcm_report=None
    try:
        for program in programs:
            for message in demo_messages(channel=midi_channel,bank=creative_bank,
                                         program=program,note=note,velocity=100):
                uart_bytes+=send_paced_frame(fd,message,conn,send)
                uart_frames+=1
            send(conn,"step 300")
            start=rowcount()
            if start<0:raise RuntimeError("P210 I/O trace disappeared")
            uart_bytes+=send_paced_frame(fd,frame(0x90|midi_channel,note,100),conn,send)
            uart_frames+=1
            send(conn,"step 850")
            uart_bytes+=send_paced_frame(fd,frame(0x80|midi_channel,note,0),conn,send)
            uart_frames+=1
            send(conn,"step 550")
            end=rowcount()
            if end<=start:
                raise RuntimeError("P210 original driver had no port writes on program "+str(program))
            windows.append({"program":program,"note":note,"velocity":100,
                            "start_row":start,"end_row":end,
                            "window_isolated":True})
    finally:
        os.close(fd)
        if pcm:pcm_report=pcm.stop()
    after=rowcount()
    if len(windows)!=expected_count or after<=before:
        raise RuntimeError("P210 complete source-driver sweep missing")
    original={
        "p89_original_first_note_trace_window":dict(windows[0]),
        ("p217_original_creative_filter_windows" if p217_sweep else "p214_original_creative_register_windows" if p214_sweep else "p212_original_creative_register_windows" if p212_sweep else "p210_original_creative_register_windows"):windows,
        "p84_midi_channel_0_based":midi_channel,
        "p75_original_private_sf2_test":False,
        "p75_program_results":[],
        "p74_uart_bytes_injected":uart_bytes,
        "p74_uart_frames_injected":uart_frames,
        "original_creative_midi_activity_register_write_delta":after-before,
        "original_creative_wavetable_audio":None,
        "direct_86box_pcm_fifo":pcm_report,
        "raw_private_audio_published":False,
        **({"p217_real_win95_filter_sweep":True} if p217_sweep else {"p214_real_win95_driver_sweep":True} if p214_sweep else {"p212_real_win95_driver_sweep":True} if p212_sweep else {"p210_real_win95_driver_sweep":True}),
        "notes":"Original Creative SBAWE.VXD and WinMM in Windows95 guest, 86Box tap, no physical board"}
    report["p64_original_win95_midi"]=original
    return original
