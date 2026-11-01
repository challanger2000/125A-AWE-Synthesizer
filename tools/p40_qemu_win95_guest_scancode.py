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
                # Win95 first launch has multiple modal warnings including
                # NE2000, daylight-saving time, and Date/Time Properties.
                # Send *actual PS/2 keyboard scancodes* and capture EACH
                # checkpoint, rather than pretending Start exists already.
                key("ret")
                time.sleep(2)
                shot("p40_024_after_network")
                key("ret")
                time.sleep(2)
                shot("p40_026_after_clock")
                key("esc")
                time.sleep(3)
                shot("p40_029_after_timezone")
                key("esc")
                time.sleep(3)
                shot("p40_032_after_second_escape")
                key("ret")
                time.sleep(5)
                shot("p40_037_after_return")
                # Once modal dialogs have cleared, test Shell and Start.
                key("ctrl-esc")
                time.sleep(4)
                shot("p40_041_guest_shell")
                key("esc")
                time.sleep(4)
                shot("p40_045_guest_shell_resumed")
                key("ctrl-esc")
                time.sleep(2)
                shot("p40_047_guest_start")
                key("r")
                time.sleep(3)
                shot("p40_050_guest_run")
                # P40c: Windows95 Run dialog at this checkpoint is
                # visually confirmed from previous P40b run. Key events go
                # directly to QEMU's PS/2 keyboard, not the CI host UI.
                command="c:\\awe32\\install.bat"
                symbols={"\\":"backslash",":":"shift-semicolon",
                         ".":"dot"," ":"spc","_":"shift-minus"}
                for ch in command:
                    key(symbols.get(ch,ch.lower()))
                time.sleep(2)
                shot("p40_052_original_installer_command")
                key("ret")
                time.sleep(14)
                shot("p40_066_original_creative_installer")
                time.sleep(11)
                shot("p40_077_original_creative_installer")
                # AWE32 is a legacy ISA device. An INF section launched
                # without a hardware instance cannot establish HKR binding.
                # Execute Win95's actual Add New Hardware wizard.
                key("ctrl-esc")
                time.sleep(1)
                key("r")
                time.sleep(1)
                for ch in "c:\\awe32\\wizard.bat":
                    key(symbols.get(ch,ch.lower()))
                time.sleep(1)
                shot("p40_080_wizard_command")
                key("ret")
                time.sleep(8)
                shot("p40_088_add_hardware_wizard")
                # Original Windows95 hardware-type list is alphabetical.
                # Select Sound, video and game controllers via "s".
                # P41c: The initial wizard focus is Next, NOT the
                # hardware-class list; sending S did nothing. Move to
                # class list with Shift+Tab, then select the Media class.
                key("shift-tab")
                time.sleep(1)
                shot("p41_089_hardware_class_list_focus")
                key("s")
                time.sleep(1)
                shot("p41_090_first_s")
                key("s")
                time.sleep(1)
                shot("p41_091_second_s")
                key("s")
                time.sleep(1)
                shot("p41_092_third_s")
                key("ret")
                time.sleep(8)
                shot("p41_100_after_class_choice")
                # Windows95 builds the device driver database on first wizard
                # invocation; 5 seconds was too short in the actual P40 run.
                # Wait for genuine guest progress rather than inventing that
                # our original Creative VxD was bound.
                time.sleep(38)
                shot("p41_133_after_database_build")
                # P41b: The 133s capture is ALREADY the manufacturer and
                # model page (default Adaptec SCSI). Previously pressing S
                # and Enter mistakenly selected a SCSI adapter. Select
                # Have Disk right here, BEFORE 'Next'.
                key("alt-h")
                time.sleep(3)
                shot("p41_136_have_disk_dialog")
                for ch in "c:\\awe32":
                    key(symbols.get(ch,ch.lower()))
                time.sleep(1)
                shot("p41_138_disk_path")
                key("ret")
                time.sleep(9)
                shot("p41_148_creative_models")
                # Capture original manufacturer/model chooser but DO NOT
                # blindly install a device without confirming AWE32 class.
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=6)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=4)
        # The booted guest may have modified SYSTEM.DAT/USER.DAT. Inspect
        # the working copy WITHOUT preserving, publishing or redistributing
        # the OS disk, Creative drivers, ROM or private SoundFont.
        report["guest_registry_verification"] = "requested"
        result=subprocess.run(
            ["python3","tools/p38_stage_creative_awe32_win95.py",
             str(disk),"--phase","verify","--output",
             str((out/"p40-guest-after-installer.json").resolve())],
            capture_output=True,text=True,timeout=40)
        report["guest_registry_check_return_code"]=result.returncode
        report["guest_registry_check_excerpt"]=(result.stdout+result.stderr)[-1100:]
    report["original_os_disk_destroyed"]=not disk.exists()
    (out/"p40-input-report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print("P40 SCREENSHOTS:",[p.name for p in out.glob("*.ppm")])
    print("P40 actual Creative VxD NOT INSTALLED. This is a keyboard-input prerequisite test.")

if __name__=="__main__":main()
