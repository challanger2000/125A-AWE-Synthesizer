#!/usr/bin/env python3
"""Stage the original 125A Win95 MIDI bridge executable in ephemeral guest FAT.

Only the new, freely-written program is copied; no Creative/Win95 binaries
or private user SF2 are uploaded to public CI artifacts.
"""
import argparse
import hashlib
import json
from pathlib import Path
from pyfatfs.PyFatFS import PyFatFS
from p38_stage_creative_awe32_win95 import partition_offset


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--disk", type=Path, required=True)
    p.add_argument("--exe", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    payload = a.exe.read_bytes()
    if len(payload) < 2048 or len(payload)>2_000_000 or payload[:2] != b"MZ":
        raise ValueError("Not a plausible i686 Win32 P63MIDI executable")
    with PyFatFS(str(a.disk), offset=partition_offset(a.disk), read_only=False,
                 preserve_case=False) as fs:
        fs.makedirs("AWE32", recreate=True)
        with fs.openbin("AWE32/P63MIDI.EXE", "w") as f:
            f.write(payload)
        if fs.readbytes("AWE32/P63MIDI.EXE") != payload:
            raise AssertionError("Win95 disk staging verification failed")
    report = {"guest_path":r"C:\AWE32\P63MIDI.EXE",
              "sha256": hashlib.sha256(payload).hexdigest(),
              "bytes":len(payload),"contains_private_user_sf2":False,
              "win95_runtime_execution_verified":False}
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
