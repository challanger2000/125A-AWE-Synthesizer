#!/usr/bin/env python3
"""Ephemeral QEMU boot probe for an unmodified, preinstalled Windows 95 image.

This script neither uploads, distributes nor commits the Windows disk image.
Reads a *copy* of the disk from a CI job. The original is never modified.
A BIOS screenshot or image-format validation is NOT a Win95-driver proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

def monitor(sock_path: Path, command: str):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(12)
        for _ in range(80):
            try:
                s.connect(str(sock_path))
                break
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(.25)
        else:
            raise RuntimeError("QEMU monitor socket never opened")
        s.recv(8192)
        s.sendall((command + "\n").encode())
        time.sleep(.5)
        answer = s.recv(65536).decode(errors="replace")
        return answer

def probe(disk_path: Path, dest: Path, checkpoints: list[int]):
    dest.mkdir(parents=True, exist_ok=True)
    if not disk_path.exists() or disk_path.stat().st_size < (200<<20):
        raise RuntimeError(f"Missing or undersized raw OS image: {disk_path}")
    original_sha256=hashlib.sha256(disk_path.read_bytes()).hexdigest()
    # Never run untrusted downloaded guest with the host network enabled.
    # Use a shadow copy: all modifications to the emulated disk are temporary.
    temporary=dest/"win95-working.img"
    shutil.copyfile(disk_path, temporary)
    monitor_path=dest/"qemu-monitor.sock"
    cmd=[
        "qemu-system-i386", "-machine", "pc,acpi=off", "-cpu", "pentium",
        "-m", "64", "-drive", f"file={temporary},format=raw,if=ide,media=disk",
        "-boot", "c", "-vga", "std", "-display", "none", "-net", "none",
        "-rtc", "base=localtime", "-no-reboot", "-serial", "none",
        "-monitor", f"unix:{monitor_path},server=on,wait=off"
    ]
    out=dest/"qemu-output.txt"
    report={
        "test": "Windows95 OSR2 v86 preinstalled raw image / QEMU boot attempt",
        "source_image_sha256": original_sha256,
        "bytes":disk_path.stat().st_size,
        "qemu_command":cmd[:],
        "network_isolated":True,
        "creative_driver_installed":False,
        "awe32_rom_loaded":False,
        "original_125a_sf2_tested":False,
        "original_win95_vxd_register_trace_captured":False,
        "qemu_boot_evidence":[],
    }
    with out.open("wb") as log:
        proc=subprocess.Popen(cmd, stdout=log,stderr=subprocess.STDOUT)
        started=time.monotonic()
        try:
            for seconds in checkpoints:
                wait=max(0,started+seconds-time.monotonic())
                time.sleep(wait)
                if proc.poll() is not None:
                    report["early_exit"]=proc.returncode
                    break
                target=dest/f"boot_{seconds:03d}.ppm"
                q=monitor(monitor_path,f"screendump {target}")
                info=monitor(monitor_path,"info status")
                exists=target.exists() and target.stat().st_size>1000
                report["qemu_boot_evidence"].append({
                   "seconds":seconds,
                   "screenshot_created":exists,
                   "screenshot":target.name if exists else None,
                   "monitor_response":q[-500:],
                   "qemu_status":info[-500:]
                })
            report["exit_before_shutdown"]=proc.poll()
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=8)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
    # Do not store the original or working OS disk in an artifact!
    temporary.unlink(missing_ok=True)
    report["image_destroyed_after_probe"]=not temporary.exists()
    (dest/"boot-status.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:v for k,v in report.items()
                     if k not in ("qemu_command","source_image_sha256")},indent=2))
    if not any(x["screenshot_created"] for x in report["qemu_boot_evidence"]):
        raise RuntimeError("No usable QEMU display capture generated")
    return report

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--image",type=Path,required=True)
    a.add_argument("--out",type=Path,default=Path("p35-output"))
    a.add_argument("--seconds",type=int,nargs="+",default=[18,55])
    args=a.parse_args()
    probe(args.image,args.out,args.seconds)
