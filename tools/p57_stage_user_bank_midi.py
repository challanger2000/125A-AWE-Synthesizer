#!/usr/bin/env python3
"""P57: stage original MIDI fixtures testing Creative's USER bank 1 selection.

The original Creative Control Panel states "User banks can be accessed using
MIDI Controller Change 0 Message." This creates bank-select MSB CC0=0 GM
control and CC0=1 User Bank 1, each followed by program0 + note48, velocity100.
No user's original SF2 or Creative ROM/OS is bundled.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
from pyfatfs.PyFatFS import PyFatFS
from p38_stage_creative_awe32_win95 import partition_offset
from p49_stage_original_midi import variable_length

def fixture(bank: int) -> bytes:
    if bank not in (0, 1):
        raise ValueError("P57 requires original Creative CC0 bank0 vs bank1")
    events = (
        b"\x00\xff\x51\x03\x07\xa1\x20" # 120 BPM
        + b"\x00\xb0\x00" + bytes([bank]) # bank select MSB CC0
        + b"\x00\xc0\x00"               # program 0 (GM piano vs P55 sine)
        + b"\x00\x90\x30\x64"           # NoteOn C3 (MIDI48) vel100
        + variable_length(1920) + b"\x80\x30\x00"
        + b"\x00\xff\x2f\x00"
    )
    return (b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)
            + b"MTrk" + struct.pack(">I", len(events)) + events)

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--disk", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    a = ap.parse_args()
    records = []
    with PyFatFS(str(a.disk), offset=partition_offset(a.disk),
                 read_only=False,preserve_case=False) as fs:
        fs.makedirs("AWE32", recreate=True)
        for bank, name in [(0,"P57-GM.MID"), (1,"P57-U1.MID")]:
            raw = fixture(bank)
            with fs.openbin("AWE32/"+name, "w") as f:
                f.write(raw)
            if fs.readbytes("AWE32/"+name) != raw:
                raise AssertionError("P57 MIDI FAT write mismatch")
            records.append({"file":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),
                            "bank_select_cc0":bank,"program_zero_based":0,
                            "midi_channel":1,"note":48,"velocity":100,"note_seconds":2})
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps({"phase":"P57","fixtures":records,
        "original_creative_user_bank_note_confirmed":False,
        "user_private_sf2_staged":False},indent=2)+"\n",encoding="utf8")
    print(json.dumps(records,indent=2))

if __name__=="__main__":
    main()
