#!/usr/bin/env python3
"""P40: QEMU monitor scancode input to Windows95, without host UI automation.

We deliberately validate that *guest* Windows95 UI responds to Ctrl+Esc and
a Run dialog before attempting Creative INF installation in a later phase.
This is an ephemeral, network-isolated, nonredistributed 512MB Windows95 disk.
"""
from __future__ import annotations
import argparse
import json
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

def hmp(sockpath, command, timeout=10):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        for i in range(100):
            try:
                s.connect(str(sockpath))
                break
            except (ConnectionRefusedError, FileNotFoundError):
                time.sleep(.15)
        else:
            raise RuntimeError("QEMU HMP monitor did not accept connections")
        s.recv(8192)
        s.sendall((command+"\n").encode("ascii"))
        time.sleep(.22)
        return s.recv(100000).decode("latin1",errors="replace")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--image",type=Path,required=True)
    p.add_argument("--out",type=Path,default=Path("p40-images"))
    args=p.parse_args()
    out=args.out
    out.mkdir(exist_ok=True,parents=True)
    report={"original_win95_guest_responds_to_qemu_scancodes":False,
            "creative_vxd_bound":False,"actual_driver_note_trace":False,
            "events":[]}
    with tempfile.TemporaryDirectory(prefix="p40-win95-") as temp:
        root=Path(temp)
        disk=root/"win95.img"
        shutil.copyfile(args.image,disk)
        mon=root/"monitor.sock"
        log=out/"qemu.log"
        command=[
           "qemu-system-i386","-machine","pc,acpi=off","-cpu","pentium",
           "-m","64","-drive",f"file={disk},format=raw,if=ide,media=disk",
           "-vga","std","-display","none","-boot","c",
           "-net","none","-rtc","base=localtime","-no-reboot",
           "-serial","none","-monitor",f"unix:{mon},server=on,wait=off"
        ]
        with log.open("wb") as f:
            proc=subprocess.Popen(command,stdout=f,stderr=subprocess.STDOUT)
            start=time.monotonic()
            def shot(label):
                target=out/(label+".ppm")
                output=hmp(mon,f"screendump {target.resolve()}")
                report["events"].append({"kind":"screen","name":label,
                                         "bytes":target.stat().st_size if target.exists() else 0,
                                         "response":output[-100:]})
            def key(s):
                ret=hmp(mon,"sendkey "+s)
                report["events"].append({"kind":"guest_scancode","key":s,
                                         "response":ret[-100:]})
            try:
                time.sleep(max(0,22-(time.monotonic()-start)))
                shot("p40_022_original_dialog")
                key("ret")
                time.sleep(3)
                shot("p40_025_after_return")
                key("esc")
                time.sleep(2)
                shot("p40_027_after_escape")
                # Windows 95 guest CTRL+ESC = launch *guest* Start Menu.
                # This is NOT the host 2022 Windows Start menu.
                key("ctrl-esc")
                time.sleep(2)
                shot("p40_029_guest_start")
                key("r")
                time.sleep(2)
                shot("p40_031_guest_run")
                for letter in "notepad":
                    key(letter)
                key("ret")
                time.sleep(7)
                shot("p40_040_guest_notepad")
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=6)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=4)
    report["original_os_disk_destroyed"]=not disk.exists()
    (out/"p40-input-report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print("P40 SCREENSHOTS:",[p.name for p in out.glob("*.ppm")])
    print("P40 actual Creative VxD NOT INSTALLED. This is a keyboard-input prerequisite test.")

if __name__=="__main__":main()
