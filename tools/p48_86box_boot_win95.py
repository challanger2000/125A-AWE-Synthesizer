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
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    if not args.disk.is_file() or args.disk.stat().st_size != 536870912:
        raise ValueError("Expected private ephemeral 512MiB Win95 guest disk")

    vm = args.out / "win95-pnp"
    write_config(vm, "sbawe32_pnp")
    cfg = vm / "86box.cfg"
    with cfg.open("a", encoding="utf8") as f:
        f.write(f"""[Storage controllers]
hdc = internal
[Hard disks]
hdd_01_fn = {args.disk.resolve()}
hdd_01_parameters = 63, 16, 1040, 0, ide
hdd_01_ide_channel = 0:0
hdd_01_speed = ramdisk
[Sound Blaster AWE32 PnP]
onboard_ram = 2048
""")
    trace = vm / "driver-potential-emu8000-io.csv"
    sockpath = vm / "automation.sock"
    env = os.environ.copy()
    env["AWE_TRACE_CSV"] = str(trace.resolve())
    env["SDL_AUDIODRIVER"] = "dummy"
    env["SDL_VIDEODRIVER"] = "x11"
    command = [str(args.binary.resolve()), "-P", str(vm.resolve()),
               "-R", str(args.roms.resolve()),
               "--automation", "unix:" + str(sockpath.resolve()),
               "--automation-hold", "--automation-seed", "12547"]

    report = {"phase": "P48", "guest": "Windows 95 OSR2, original Creative INF staged and installed in QEMU",
              "hardware": "86Box AWE32 PnP",
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
                if info.get("sound") != "sbawe32_pnp":
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
                guest_sf2_path = "c:\\awe32\\p62test.sf2"
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
                send(conn, "step 4000")
                p49_screenshot(conn, args.out, "p56-apply-result-5s.png", report)
                io_after_apply = (
                    len(trace.read_text(encoding="utf8", errors="replace").splitlines())-1
                    if trace.is_file() else 0
                )
                report["p56_staged_sf2"] = guest_sf2_path
                report["p56_apply_attempted"] = True
                report["p56_register_writes_after_apply"] = max(
                    0,io_after_apply-io_before_apply)
                # P60: inspect only the original Creative sample-memory
                # upload span, before any subsequent MIDI note messages.
                # Upload private CSV contents stay in ephemeral runner.
                if trace.is_file():
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
                report["p62_wideband_upload_only"] = True
                                report["p55_original_sf2_load_confirmed"] = False
                report["p53_original_control_panel_loaded"] = False
                report["p53_original_bank_sf2_loaded"] = False
                report["p53_86box_sample_ram_kb"] = 2048
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
                    report["raw_emu8000_preview"] = lines[1:4]
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
