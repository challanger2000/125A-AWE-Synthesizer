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
                # P49: The actual Win95 desktop and focused Welcome Close
                # were visually confirmed in successful P48b run #41349407124.
                # Open Win95 Start -> Run via known Ctrl+Esc, R shortcut.
                # A screenshot is saved BEFORE sending the laboratory path.
                send(conn, "key down 0x1d 0x01")
                send(conn, "key up 0x01 0x1d")
                send(conn, "step 300")
                p49_key(conn, 0x13)       # r => Win95 Run menu item
                send(conn, "step 500")
                p49_screenshot(conn, args.out, "p49-run-dialog.png", report)
                fixture_path = "c:\\awe32\\p49-p7.mid"
                # Verified historical Windows 95 MPLAYER.EXE command-line
                # switch: /play starts playback rather than opening stopped.
                play_command = "c:\\windows\\mplayer.exe /play " + fixture_path
                p49_type_path(conn, play_command)
                p49_screenshot(conn, args.out, "p49-run-midi-path.png", report)
                report["requested_midi_path"] = fixture_path
                report["requested_midi_program"] = 7
                report["requested_midi_command"] = play_command
                # Do not assert the MIDI is routed to AWE32 until Windows
                # player UI and register/audio changes actually prove it.
                baseline = 0
                if trace.exists():
                    baseline = max(0, len(trace.read_text(encoding="utf8", errors="replace").splitlines()) - 1)
                report["raw_writes_before_midi_launch"] = baseline
                try:
                    send(conn, "audio start")
                    report["automation_audio_recording_started"] = True
                except Exception as exc:
                    report["audio_recording_error"] = str(exc)
                p49_key(conn, 0x1c)       # launch fixed laboratory .MID
                report["midi_open_command_entered"] = True
                send(conn, "step 1000")
                p49_screenshot(conn, args.out, "p49-midi-player-initial.png", report)
                send(conn, "step 4000")
                p49_screenshot(conn, args.out, "p49-midi-player-after4s.png", report)
                try:
                    levels = send(conn, "audio level 5000")
                    report["post_midi_audio_levels"] = levels
                except Exception as exc:
                    report["audio_level_error"] = str(exc)
                try:
                    audio = send(conn, "audio stop")
                    report["audio_segments"] = [
                        {k: v for k, v in seg.items() if k not in ("file",)}
                        for seg in audio.get("segments", [])
                    ]
                except Exception as exc:
                    report["audio_stop_error"] = str(exc)
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
                    report["raw_writes_after_midi_launch_delta"] = max(0, len(lines)-1-baseline)
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
