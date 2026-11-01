#!/usr/bin/env python3
"""P47: inspect an isolated instrumented 86Box VM via its automation socket.

The 'sbawe32' test uses explicit client I/O and is a SYNTHETIC register
smoke check, not an original Creative-driver trace. The 'sbawe32_pnp' test
only proves that the AWE32 PnP card is instantiated (not yet bound to Win95).
No Windows disk or private driver/sample bank is read by this program.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import socket
import subprocess
import time
from pathlib import Path


def send(conn: socket.socket, command: str) -> dict:
    conn.sendall((command + "\n").encode("ascii"))
    data = bytearray()
    while not data.endswith(b"\n"):
        chunk = conn.recv(1024 * 1024)
        if not chunk:
            raise RuntimeError("86Box automation socket closed before a reply")
        data.extend(chunk)
        if len(data) > 2_000_000:
            raise RuntimeError("Unexpected oversized automation reply")
    reply = json.loads(data.decode("utf8"))
    if not reply.get("ok", False):
        raise RuntimeError(f"86Box rejected {command!r}: {reply}")
    return reply


def wait_socket(path: Path, proc: subprocess.Popen, timeout: float) -> socket.socket:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"86Box exited early, return code {proc.returncode}")
        try:
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            conn.settimeout(15)
            conn.connect(str(path))
            return conn
        except (FileNotFoundError, ConnectionRefusedError, OSError):
            conn.close()
            time.sleep(0.3)
    raise TimeoutError(f"86Box automation socket not found: {path}")


def write_config(vm: Path, card: str) -> None:
    vm.mkdir(parents=True, exist_ok=True)
    (vm / "86box.cfg").write_text(f"""[General]
vid_renderer = sdl_software
confirm_exit = 0
[Machine]
machine = p55t2p4
cpu_family = pentium_p54c
cpu_speed = 133333333
cpu_multi = 2
cpu_use_dynarec = 1
fpu_type = internal
mem_size = 65536
time_sync = disabled
[Video]
gfxcard = vga
[Input devices]
keyboard_type = keyboard_at
mouse_type = ps2
[Sound]
sndcard = {card}
[Network]
net_01_link = 0
""", encoding="utf8")


def check_trace(csv_path: Path) -> dict:
    if not csv_path.exists():
        raise AssertionError("No EMU8000 CSV after the synthetic I/O writes")
    data = csv_path.read_text(encoding="utf8").splitlines()
    if not data or data[0] != "sequence,wc,port,value,pointer,reg,voice,kind":
        raise AssertionError(f"EMU8000 CSV header wrong or missing: {data[:2]}")
    if not any(",0xe22,0x0020," in x and x.endswith(",pointer") for x in data[1:]):
        raise AssertionError("Pointer register write not observed")
    if not any(",0x620,0x1234," in x and x.endswith(",data") for x in data[1:]):
        raise AssertionError("Data register write not observed")
    return {"data_lines": len(data) - 1, "header": data[0],
            "pointer_confirmed": True, "data_confirmed": True}


def run_one(args: argparse.Namespace, card: str) -> dict:
    vm = args.out / card
    write_config(vm, card)
    trace = (vm / "emu8000-io.csv").resolve()
    sockpath = (vm / "automation.sock").resolve()
    logfile = vm / "86box.log"
    env = os.environ.copy()
    env["AWE_TRACE_CSV"] = str(trace)
    env["SDL_AUDIODRIVER"] = "dummy"
    env["SDL_VIDEODRIVER"] = "x11"
    command = [str(args.binary.resolve()), "-P", str(vm.resolve()),
               "-R", str(args.roms.resolve()),
               "--automation", "unix:" + str(sockpath),
               "--automation-hold"]
    with logfile.open("wb") as log:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        try:
            with wait_socket(sockpath, proc, 35) as conn:
                info = send(conn, "info")
                status = send(conn, "status")
                if not status.get("held", False):
                    raise AssertionError("Automation-hold was not effective")
                info_text = json.dumps(info, sort_keys=True)
                if card not in info_text and "AWE32" not in info_text:
                    raise AssertionError(f"Expected {card} not found in 86Box info: {info_text[:1500]}")
                result = {"card": card, "status": {"held": status["held"]},
                          "machine_info": info, "emulated_windows95_driver": False,
                          "real_hardware_trace": False}
                if card == "sbawe32":
                    # Directly inject two *synthetic* I/O writes through the
                    # 86Box automation client. These do NOT originate from
                    # Win95/SBAWE.VXD; do not label them as driver evidence.
                    send(conn, "iow 0xe22 2 0x20")
                    send(conn, "iow 0x620 2 0x1234")
                    send(conn, "step 1")
                    result["synthetic_io_trace"] = check_trace(trace)
                else:
                    # ISA PnP requires device/resource activation by BIOS or
                    # guest driver; unconfigured ports may not be mapped here.
                    result["pnp_card_present_only"] = True
                try:
                    send(conn, "quit")
                except Exception:
                    pass
                return result
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--roms", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    checks = []
    report = {"phase": "P47", "hardware": "86Box EMU8000 emulator",
              "driver_trace_captured": False, "physical_card_tested": False,
              "checks": checks}
    try:
        for card in ("sbawe32", "sbawe32_pnp"):
            checks.append(run_one(args, card))
        report["success"] = True
    except Exception as exc:
        report["success"] = False
        report["error"] = str(exc)
        raise
    finally:
        (args.out / "P47-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
