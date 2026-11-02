#!/usr/bin/env python3
"""Enable Win95 WIN.INI legacy autostart for the CRT-free P68 agent launcher.

Runs after the original Creative driver installation/guest disk handoff.
The caller's disposable image is the only modified artifact.
No licensed Microsoft, Creative or private SoundFont bytes leave the runner.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

LAUNCHER = r"C:\AWE32\P68BOOT.EXE"
MAX_EXE = 100_000
def patch_win_ini(buf: bytes) -> bytes:
    text=buf.decode("latin-1")
    newline="\r\n" if "\r\n" in text else "\n"
    lines=text.splitlines()
    windows=False
    found_section=False
    found_run=False
    result=[]
    for line in lines:
        if line.lstrip().startswith("[") and "]" in line:
            if windows and not found_run:
                result.append("run="+LAUNCHER)
                found_run=True
            windows=(line.strip().lower()=="[windows]")
            found_section|=windows
        if windows and re.match(r"^\s*run\s*=",line,re.I):
            previous=line.split("=",1)[1].strip()
            if LAUNCHER.lower() in previous.lower():
                new=line
            elif previous:
                new="run="+previous+" "+LAUNCHER
            else:
                new="run="+LAUNCHER
            result.append(new)
            found_run=True
        else:
            result.append(line)
    if windows and not found_run:
        result.append("run="+LAUNCHER)
        found_run=True
    if not found_section or not found_run:
        raise ValueError("WIN.INI [windows] run= entry not found or not writable")
    return (newline.join(result)+newline).encode("latin-1")

def stage(disk: Path, launcher: Path) -> dict:
    from pyfatfs.PyFatFS import PyFatFS
    from p38_stage_creative_awe32_win95 import partition_offset
    raw=launcher.read_bytes()
    if not 512<=len(raw)<=MAX_EXE or raw[:2]!=b"MZ":
        raise ValueError("Unexpected or missing Win95 CRT-free launcher EXE")
    with PyFatFS(str(disk),offset=partition_offset(disk),
                 read_only=False,preserve_case=False) as fs:
        if not fs.exists("AWE32/P63MIDI.EXE"):
            raise FileNotFoundError("P63 MIDI guest agent missing from disposable disk")
        if not fs.exists("WINDOWS/WIN.INI"):
            raise FileNotFoundError("Win95 WIN.INI missing from disposable disk")
        old=fs.readbytes("WINDOWS/WIN.INI")
        new=patch_win_ini(old)
        with fs.openbin("WINDOWS/WIN.INI","w") as f:
            f.write(new)
        if fs.readbytes("WINDOWS/WIN.INI")!=new:
            raise AssertionError("WIN.INI autostart write did not persist")
        with fs.openbin("AWE32/P68BOOT.EXE","w") as f:
            f.write(raw)
        if fs.readbytes("AWE32/P68BOOT.EXE")!=raw:
            raise AssertionError("P68 launcher write did not persist")
    return {"phase":"P68","guest_autostart":LAUNCHER,
        "launcher_sha256":hashlib.sha256(raw).hexdigest(),
        "agent_staged":True,
        "run_entry_persisted":True,
        "win95_original_creative_midi_verified":False}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--disk",type=Path,required=True)
    ap.add_argument("--launcher",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    a=ap.parse_args()
    report=stage(a.disk,a.launcher)
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
