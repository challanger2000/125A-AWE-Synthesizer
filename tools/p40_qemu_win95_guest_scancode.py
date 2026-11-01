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
    p.add_argument("--guest-keep-copy", type=Path, default=None,
                   help="Private TEMPORARY guest disk handoff to another CI step; never publish")
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
           "-net","none","-rtc","base=localtime",
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
                # P42: Evidence from P41b screenshot proves the class list
                # is already OPEN and FOCUSED at this exact checkpoint.
                # It starts on CD-ROM controllers. Typing s moves to SCSI.
                # The immediately following entry is Sound, video and game
                # controllers. Never Shift+Tab here: P41c/P41d showed that
                # this moves focus onto Cancel instead of the class list.
                key("s")
                time.sleep(2)
                shot("p42_090_scsi_selected")
                key("down")
                time.sleep(2)
                shot("p42_092_sound_video_game_controllers")
                key("ret")
                # The original Win95 model database may need time to build.
                time.sleep(43)
                shot("p42_135_media_manufacturer_model_page")
                # Have Disk is only meaningful for Class=MEDIA selection.
                key("alt-h")
                time.sleep(3)
                shot("p42_138_install_from_disk")
                for ch in "c:\\awe32":
                    key(symbols.get(ch,ch.lower()))
                time.sleep(2)
                shot("p42_140_original_creative_driver_path")
                key("ret")
                time.sleep(10)
                shot("p42_150_creative_awe32_model_candidates")
                # P43: P42 screenshot verified this exact dialog is the
                # original Creative Select Device list. Index 0 is Creative
                # 3D Stereo Enhancement Technology. Index 1 is:
                # Creative Advanced Wave Effects Synthesis for AWE 32.
                # Select that original driver by one DOWN. Capture the
                # proposed device BEFORE confirming it.
                key("down")
                time.sleep(2)
                shot("p43_152_awe32_synthesis_model_selected")
                key("ret")
                time.sleep(15)
                shot("p43_170_after_original_awe32_model_confirmation")
                # P44: P43 evidence shows the actual Win95 "Windows can
                # continue installing your hardware now" page with a
                # focused FINISH button. Confirm precisely that button once.
                # Subsequent dialogs remain unverified: do not automate
                # additional confirmations until their screenshots are read.
                key("ret")
                time.sleep(13)
                shot("p44_183_after_finish")
                time.sleep(25)
                shot("p44_208_after_driver_setup")
                # P46: The P44 screenshot explicitly requests a restart,
                # with YES already focused. This VM now allows guest reboot
                # instead of QEMU's previous -no-reboot shutdown behavior.
                key("ret")
                time.sleep(18)
                shot("p46_226_after_original_win95_reboot")
                time.sleep(40)
                shot("p46_266_win95_postboot_driver_state")
                report["p46_restart_requested"]=True
                report["p46_original_awe32_driver_bound"]="not yet proven"
                report["p46_note_on_register_trace"]=False
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
        if args.guest_keep_copy is not None:
            # The QEMU working image is destroyed on context exit. This
            # handoff remains only in RUNNER_TEMP during the SAME CI job,
            # solely to boot original drivers on emulated AWE32 in 86Box.
            target = args.guest_keep_copy.resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(disk, target)
            report["private_guest_handoff"] = "ephemeral runner only"
            report["private_guest_size"] = target.stat().st_size

    report["original_os_disk_destroyed"]=not disk.exists()
    (out/"p40-input-report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print("P40 SCREENSHOTS:",[p.name for p in out.glob("*.ppm")])
    print("P40 actual Creative VxD NOT INSTALLED. This is a keyboard-input prerequisite test.")

if __name__=="__main__":main()
