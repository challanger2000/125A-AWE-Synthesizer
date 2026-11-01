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
                for elapsed in (15000, 30000, 60000):
                    step = send(conn, f"step {elapsed}")
                    report["last_emulated_ms"] = step.get("ms")
                    name = f"win95-{step.get('ms', 0):08d}.png"
                    target = args.out / name
                    try:
                        screen = send(conn, f"screenshot {target.resolve()}")
                        report["screens"].append({"name": name, "w": screen.get("w"), "h": screen.get("h")})
                    except Exception as exc:
                        report["screens"].append({"name": name, "error": str(exc)})
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
