#!/usr/bin/env python3
"""P48: boot the private P46-installed Win95 disk with REAL 86Box AWE32 PnP emulation.

Driver/device binding remains UNPROVEN until Windows 95 itself confirms it.
No guest disk, Creative driver, or ROM is committed or placed in artifacts.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from pathlib import Path

from p47_86box_emu8k_smoke import send, wait_socket, write_config
from p50_emu8k_midi_probe import play as p50_play
from p58_analyze_audio import analyze_wav
from p60_compare_creative_sf2_upload import analyze as p60_analyze_upload
from p64_original_win95_midi_trial import run_trial as p64_run_trial
from p75_private_sf2 import stage as p75_stage_private_sf2
from p80_full_sf2_inventory import inventory as p80_inventory
from p76_export_private_wav import export as p76_export_private_wav
from p83_generic_sf2 import stage_private as p83_stage_private
from p84_export_universal_wav import export as p84_export_universal_wav


# Scancode set 1 (US Win95 layout), only for the fixed laboratory filename.
P49_KEYCODES = {
    **dict(zip("qwertyuiop", range(0x10, 0x1a))),
    **dict(zip("asdfghjkl", range(0x1e, 0x27))),
    **dict(zip("zxcvbnm", range(0x2c, 0x33))),
    **dict(zip("1234567890", list(range(0x02, 0x0c)))),
    "\\": 0x2b, ".": 0x34, "-": 0x0c, "/": 0x35, " ": 0x39,
}


def p49_key(conn: socket.socket, scan: int) -> None:
    send(conn, f"key down 0x{scan:x}")
    send(conn, f"key up 0x{scan:x}")


def p49_type_path(conn: socket.socket, value: str) -> None:
    for ch in value.lower():
        if ch == ":":
            send(conn, "key down 0x2a")  # shift + semicolon
            p49_key(conn, 0x27)
            send(conn, "key up 0x2a")
        else:
            scan = P49_KEYCODES.get(ch)
            if scan is None:
                raise ValueError(f"Unsupported P49 test filename character {ch!r}")
            p49_key(conn, scan)


def p49_screenshot(conn: socket.socket, out: Path, name: str, report: dict) -> None:
    result = send(conn, f"screenshot {(out / name).resolve()}")
    report["screens"].append({"name": name, "w": result.get("w"), "h": result.get("h")})



def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--roms", type=Path, required=True)
    ap.add_argument("--disk", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--p64-bridge", action="store_true", help="Run original Win95 MIDI agent through 86Box COM1")
    ap.add_argument("--private-sf2", type=Path, help="Local original SF2, never commit/upload")
    ap.add_argument("--universal-sf2",type=Path,help="Any private SF2; original Creative Win95 driver audition")
    ap.add_argument("--universal-sf2-bank",type=int,help="SF2 preset bank; default first present bank")
    ap.add_argument("--universal-programs",help="Comma-separated two SF2 MIDI programs; defaults to first two")
    ap.add_argument("--universal-creative-bank",type=int,default=1,help="Win95 Creative user bank (CC0), default 1")
    ap.add_argument("--universal-note",type=int,default=60,help="MIDI audition note (drum kits: 36)")
    ap.add_argument("--universal-wav-dir",type=Path,help="Private output directory of real original Creative WAVs")
    ap.add_argument("--require-full-bank",action="store_true",help="Require exact original 77-preset bank, not the two-preset test fixture")
    ap.add_argument("--private-wav-dir",type=Path,help="Local private export directory for original two bass WAVs")
    ap.add_argument("--sound-card", choices=("sbawe32_pnp","sbawe64_gold"), default="sbawe32_pnp")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if not args.disk.is_file() or args.disk.stat().st_size != 536870912:
        raise ValueError("Expected private ephemeral 512MiB Win95 guest disk")

    if args.private_sf2 and args.universal_sf2:
        raise ValueError("Specify exactly one original or universal SF2 mode")
    if args.require_full_bank and args.universal_sf2:
        raise ValueError("Full77 fixture is incompatible with universal SF2 mode")
    if args.universal_sf2 and not args.p64_bridge:
        raise ValueError("--universal-sf2 requires --p64-bridge")
    if args.universal_wav_dir and not args.universal_sf2:
        raise ValueError("--universal-wav-dir requires --universal-sf2")
    if args.private_sf2 and not args.p64_bridge:
        raise ValueError("--private-sf2 requires --p64-bridge")
    if args.private_wav_dir and not args.private_sf2:
        raise ValueError("--private-wav-dir requires --private-sf2")
    if args.require_full_bank and not args.private_sf2:
        raise ValueError("--require-full-bank requires --private-sf2")
    full_bank_report=p80_inventory(args.private_sf2.read_bytes()) if args.require_full_bank else None
    ram_kib=28672 if args.sound_card=="sbawe64_gold" else 2048
    generic_report=p83_stage_private(args.disk,args.universal_sf2,ram_kib*1024) if args.universal_sf2 else None
    if generic_report:
        generic_report["sample_data_bytes"]=generic_report["sample_pcm_bytes"]
        bank=(args.universal_sf2_bank if args.universal_sf2_bank is not None
              else generic_report["available_banks"][0])
        available=[item for item in generic_report["presets"] if item["bank"]==bank]
        if not available:
            raise ValueError("Requested SF2 bank %d contains no presets"%bank)
        if args.universal_programs:
            raw=args.universal_programs.split(",")
            if len(raw)!=2:raise ValueError("Exactly two MIDI test programs required")
            selected=[int(v.strip()) for v in raw]
        else:
            selected=[item["program"] for item in available[:2]]
            if len(selected)==1:selected.append(selected[0])
        if len(selected)!=2 or any(not 0<=pr<=127 for pr in selected):
            raise ValueError("Need two valid MIDI test programs")
        by_program={item["program"]:item for item in available}
        if any(pr not in by_program for pr in selected):
            raise ValueError("Selected MIDI program absent in SF2 bank %d"%bank)
        audition_presets=[by_program[pr] for pr in selected]
        if not 0<=args.universal_note<=127 or not 0<=args.universal_creative_bank<=127:
            raise ValueError("Universal MIDI note and Creative bank must be 0..127")
    else:
        audition_presets=[]
    private_report=(generic_report if generic_report else
                    p75_stage_private_sf2(args.disk,args.private_sf2) if args.private_sf2 else None)
    card_section={"sbawe32_pnp":"Sound Blaster AWE32 PnP",
                  "sbawe64_gold":"Sound Blaster AWE64 Gold"}[args.sound_card]
    vm = args.out / "win95-pnp"
    write_config(vm, args.sound_card)
    cfg = vm / "86box.cfg"
    with cfg.open("a", encoding="utf8") as f:
        f.write(f"""[Storage controllers]
hdc = internal
[Hard disks]
hdd_01_fn = {args.disk.resolve()}
hdd_01_parameters = 63, 16, 1040, 0, ide
hdd_01_ide_channel = 0:0
hdd_01_speed = ramdisk
[{card_section}]
onboard_ram = {ram_kib}
""")
    if args.p64_bridge:
        # 86Box 2026 Linux char_pipe server: *.in is guest RX, *.out is TX.
        # P64 writes the host MIDI into *.in without injecting EMU8000 registers.
        with cfg.open("a",encoding="utf8") as f:
            f.write("""[Ports (COM & LPT)]
serial1_enabled = 1
serial1_device = pipe
[Named Pipe (COM) #1]
path = """+str((vm/"p64-midi").resolve())+"""
mode = 1
reconnect = 1
""")
    trace = vm / "driver-potential-emu8000-io.csv"
    sockpath = vm / "automation.sock"
    env = os.environ.copy()
    env["AWE_TRACE_CSV"] = str(trace.resolve())
    env["SDL_AUDIODRIVER"] = "dummy"
    env["SDL_VIDEODRIVER"] = "x11"
    if args.p64_bridge:
        env["AWE_P65_PCM_FIFO"] = str((vm/"p65-wavetable").resolve())
    command = [str(args.binary.resolve()), "-P", str(vm.resolve()),
               "-R", str(args.roms.resolve()),
               "--automation", "unix:" + str(sockpath.resolve()),
               "--automation-hold", "--automation-seed", "12547"]

    report = {"phase": "P48", "guest": "Windows 95 OSR2, original Creative INF staged and installed in QEMU",
              "hardware": args.sound_card, "sample_ram_kib": ram_kib,
              "private_sf2_supplied":bool(private_report),
              "p84_universal_sf2_test":bool(generic_report),
              "p84_selected_presets":audition_presets,
              "p84_creative_user_bank":args.universal_creative_bank if generic_report else None,
              "p84_synthesizer_sample_bytes":generic_report["sample_pcm_bytes"] if generic_report else None,
              "full_77_preset_soundfont_validated":bool(full_bank_report),
              "full_77_preset_sample_bytes":full_bank_report["sample_data_bytes"] if full_bank_report else None,
              "windows95_binding_verified": False, "actual_driver_note_trace_verified": False,
              "source_sf2_tested": False, "screens": []}
    with (args.out / "86box-win95-host.log").open("wb") as log:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        try:
            with wait_socket(sockpath, proc, 50) as conn:
                conn.settimeout(300)
                info = send(conn, "info")
                report["machine"] = info.get("machine")
                report["sound"] = info.get("sound")
                report["hdd_present"] = bool(info.get("hdd"))
                if info.get("sound") != args.sound_card:
                    raise AssertionError("Wrong emulated card in P48 VM")
                if not info.get("hdd"):
                    raise AssertionError("Win95 IDE disk was not mounted")
                for index, elapsed in enumerate((15000, 30000, 5000, 15000, 30000, 30000)):
                    step = send(conn, f"step {elapsed}")
                    report["last_emulated_ms"] = step.get("ms")
                    name = f"win95-{step.get('ms', 0):08d}.png"
                    target = args.out / name
                    try:
                        screen = send(conn, f"screenshot {target.resolve()}")
                        report["screens"].append({"name": name, "w": screen.get("w"), "h": screen.get("h")})
                    except Exception as exc:
                        report["screens"].append({"name": name, "error": str(exc)})
                    if index == 0:
                        # Verified P48 run 41347661011: first-ever boot of
                        # ASUS P/I-P55T2P4 BIOS displays "CMOS checksum
                        # error — Defaults loaded" and "Press F1 to
                        # continue". Press that observed key exactly once.
                        # Screenshot is saved BEFORE input for audit.
                        send(conn, "key down 0x3b")
                        send(conn, "key up 0x3b")
                        report["f1_cmos_continue_pressed"] = True
                    if index == 1:
                        # P48 run #41348535559: Windows 95 reaches a
                        # centered "Windows Networking" warning about the
                        # mismatched NE2000 device. "OK" has keyboard
                        # focus. Press Enter ONCE, after saving screenshot,
                        # without changing any actual guest driver state.
                        send(conn, "key down 0x1c")
                        send(conn, "key up 0x1c")
                        report["ne2000_warning_ok_pressed"] = True
                    if index == 3:
                        # P48b screenshot 00065008: Win95 Welcome window
                        # shows a focused Close button. Press Enter only once.
                        p49_key(conn, 0x1c)
                        report["win95_welcome_closed"] = True
                # P50: P49b run #41351601157 confirmed
                # MPLAYER.EXE /play actually PLAYING MIDI program 0,
                # 163 fresh EMU8000 writes, wavetable peak -32.8 dBFS.
                # Run both staged GM fixtures in the SAME original Win95 VM.
                # The program 0/7 tests are baseline device-compatibility
                # tests, NOT a check against the user's exact SF2 basses.
                report["p50_midi_trials"] = []
                for program in (0, 7):
                    trial = p50_play(
                        conn, args.out, trace, program,
                        key=p49_key, type_path=p49_type_path,
                        screenshot=p49_screenshot, report=report,
                    )
                    report["p50_midi_trials"].append(trial)
                # P53: load the ORIGINAL Creative AWE Control Panel from
                # an ephemeral guest directory. It is not a user-bank
                # loader substitute. First close the MIDI player, then
                # use the Win95 Start/Run UI that succeeded in P49.
                send(conn, "key down 0x38 0x3e")   # Alt-F4 closes MPLAYER
                send(conn, "key up 0x3e 0x38")
                send(conn, "step 350")
                send(conn, "key down 0x1d 0x01")   # Ctrl+Esc => Start
                send(conn, "key up 0x01 0x1d")
                send(conn, "step 300")
                p49_key(conn, 0x13)                 # 'R' = Run
                send(conn, "step 500")
                p49_screenshot(conn, args.out, "p53-control-panel-run.png", report)
                cp_cmd = "c:\\awe32\\cp\\awecp32.exe"
                p49_type_path(conn, cp_cmd)
                p49_screenshot(conn, args.out, "p53-control-panel-command.png", report)
                report["p53_control_panel_command"] = cp_cmd
                p49_key(conn, 0x1c)
                send(conn, "step 7000")
                p49_screenshot(conn, args.out, "p53-control-panel-open.png", report)
                # P54: verify the ORIGINAL Creative Control Panel pages,
                # without asserting a bank is loaded or changing preferences.
                # Standard Win95 property-sheet Ctrl+Tab switches tab.
                for pane in ("synth", "user", "wavefx", "playback"):
                    send(conn, "key down 0x1d 0x0f")  # Ctrl + Tab
                    send(conn, "key up 0x0f 0x1d")
                    send(conn, "step 800")
                    p49_screenshot(conn, args.out,
                                   f"p54-creative-{pane}-tab.png", report)
                report["p54_original_cp_tabs_screenshotted"] = True
                # P55: return from Playback via WaveFx to User.
                for _ in range(2):
                    send(conn, "key down 0x1d 0x2a 0x0f") # Ctrl+Shift+Tab
                    send(conn, "key up 0x0f 0x2a 0x1d")
                    send(conn, "step 600")
                p49_screenshot(conn, args.out, "p55-user-before-browse.png", report)
                # Creative User tab has a 'Browse...' button. Try its
                # standard Windows-95 Alt+B mnemonic, but do not type into
                # an unconfirmed dialog or claim any SoundFont is loaded.
                send(conn, "key down 0x38 0x30") # Alt+B
                send(conn, "key up 0x30 0x38")
                send(conn, "step 800")
                p49_screenshot(conn, args.out, "p55-after-alt-b.png", report)
                report["p55_user_browse_requested"] = True
                # P56: P55 screenshot establishes the Win95 common
                # dialog has "File Name" focused and "*.sbk;*.sf2" selected.
                # Enter the staged path exactly, confirm via Return.
                guest_sf2_path = ("c:\\awe32\\p83user.sf2" if generic_report else
                                  "c:\\awe32\\p75user.sf2" if private_report else
                                  "c:\\awe32\\p55test.sf2" if args.p64_bridge else
                                  "c:\\awe32\\p62test.sf2")
                p49_type_path(conn, guest_sf2_path)
                p49_screenshot(conn, args.out, "p56-file-selected.png", report)
                p49_key(conn, 0x1c)
                send(conn, "step 1500")
                p49_screenshot(conn, args.out, "p56-after-file-open.png", report)
                # AWECP32 User pane requires Apply. Attempt standard
                # Alt+A mnemonic and capture UI as evidence, including
                # any Creative native bank parser errors.
                io_before_apply = (
                    len(trace.read_text(encoding="utf8", errors="replace").splitlines())-1
                    if trace.is_file() else 0
                )
                send(conn, "key down 0x38 0x1e") # Alt+A
                send(conn, "key up 0x1e 0x38")
                send(conn, "step 1500")
                p49_screenshot(conn, args.out, "p56-apply-result-1s.png", report)
                send(conn, "step 10000" if full_bank_report else "step 4000")
                p49_screenshot(conn, args.out, "p56-apply-result-5s.png", report)
                io_after_apply = (
                    len(trace.read_text(encoding="utf8", errors="replace").splitlines())-1
                    if trace.is_file() else 0
                )
                report["p56_staged_sf2"] = guest_sf2_path
                report["p56_apply_attempted"] = True
                report["p56_register_writes_after_apply"] = max(
                    0,io_after_apply-io_before_apply)
                if private_report:
                    # Don't mistake GM ROM fallback for the user's bank.
                    # Creative SF2 upload writes its PCM into EMU8000 sample
                    # memory via the known voice26/reg1 data port. Count only
                    # the actual Apply window, never generic register writes.
                    import csv
                    user_words=0
                    if trace.is_file():
                        with trace.open("r",encoding="utf8",errors="replace") as source:
                            for idx,row in enumerate(csv.DictReader(source)):
                                if idx<io_before_apply:continue
                                if idx>=io_after_apply:break
                                if (row.get("kind")=="data"
                                    and row.get("reg")=="1"
                                    and row.get("voice")=="26"
                                    and row.get("port","").lower() in ("0x0a20","0x0a22")):
                                    user_words+=1
                    expected=private_report["sample_data_bytes"]//2
                    # A full 77-preset bank must not be accepted on the
                    # basis of a tiny partial upload or the GM ROM bank.
                    minimum=(expected*9//10 if (full_bank_report or generic_report) else max(128,expected//8))
                    report["p75_private_sample_upload_write_words"]=user_words
                    report["p75_private_sample_upload_minimum_words"]=minimum
                    report["p75_private_sample_upload_plausible"]=user_words>=minimum
                # P60: inspect only the original Creative sample-memory
                # upload span, before any subsequent MIDI note messages.
                # Upload private CSV contents stay in ephemeral runner.
                if trace.is_file() and not args.p64_bridge:
                    report["p60_original_sf2_upload"] = p60_analyze_upload(
                        trace, io_before_apply, io_after_apply)
                # These flags require *visual inspection* and evidence of
                # successful original Creative user-bank load/DRAM delta.
                report["p56_original_sf2_load_verified"] = False
                # P57: same note through historical Creative MIDI stack,
                # first GM bank 0, then AWECP32 USER bank 1 (CC0=1).
                # No synthetic I/O injection: only original guest MPLAYER.
                # P62 isolates sample transfer. Original MIDI audio/spectrum
                # probes from P57/P58 are deliberately omitted: this bank
                # contains a wideband probe, not the earlier P55 sine.
                report["p57_original_midi_trials"] = []
                report["p62_wideband_upload_only"] = not args.p64_bridge
                if args.p64_bridge:
                    p64_run_trial(conn,args.out,trace,vm/"p64-midi",send,
                                  p49_key,p49_type_path,p49_screenshot,report,
                                  pcm_fifo=vm/"p65-wavetable",
                                   programs=tuple(item["program"] for item in audition_presets) if generic_report else ((0,7) if private_report else (0,)),
                                   note=args.universal_note if generic_report else 48,
                                   creative_bank=args.universal_creative_bank if generic_report else 1,
                                   preset_names={item["program"]:item["name"] for item in audition_presets} if generic_report else ({0:"Grungy Ramp Bass",7:"TX81Z Lately Bass"} if private_report else None))
                    if args.universal_wav_dir:
                        report["p84_universal_wav_export"]=p84_export_universal_wav(
                            args.out,args.universal_wav_dir,report)
                    if args.private_wav_dir:
                        report["p76_private_wav_export"]=p76_export_private_wav(
                            args.out,args.private_wav_dir,report)
                report["p55_original_sf2_load_confirmed"] = False
                report["p53_original_control_panel_loaded"] = False
                report["p53_original_bank_sf2_loaded"] = False
                report["p53_86box_sample_ram_kb"] = ram_kib
                try:
                    status = send(conn, "status")
                    report["end_status"] = {
                        "ms": status.get("ms"), "frames": status.get("frames"),
                        "bios_mode": status.get("bios_mode")}
                    report["screen_active"] = bool(status.get("w") and status.get("h"))
                except Exception as exc:
                    report["status_error"] = str(exc)
                # Any writes could be init or driver. Do not call them actual
                # Creative note traces without Windows driver/patch evidence.
                if trace.exists():
                    lines = trace.read_text(encoding="utf8", errors="replace").splitlines()
                    report["raw_emu8000_write_count"] = max(0, len(lines) - 1)
                    report["raw_emu8000_preview"] = [] if private_report else lines[1:4]
                    report["raw_writes_after_two_midi_launches_delta"] = max(
                        0, len(lines)-1-report["p50_midi_trials"][0]["raw_writes_before"])
                    report["raw_emu8000_pointer_count"] = sum(
                        x.endswith(",pointer") for x in lines[1:])
                    report["raw_emu8000_data_count"] = sum(
                        x.endswith(",data") for x in lines[1:])
                try:
                    send(conn, "quit")
                except (OSError, RuntimeError):
                    pass
                report["success"] = True
        except Exception as exc:
            report["success"] = False
            report["error"] = str(exc)
            raise
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            (args.out / "P48-report.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf8")
            print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
