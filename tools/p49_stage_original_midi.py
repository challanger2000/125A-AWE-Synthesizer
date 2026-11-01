#!/usr/bin/env python3
"""P49: stage deterministic original MIDI fixtures in the disposable Win95 FAT disk.

No SF2 or ROM data is copied. The two short MIDI files contain a single
C3 note (MIDI 48) at velocity 100, once on GM program 0 and once on 7.
MIDI files are original programmatically generated test data, not song files.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from pyfatfs.PyFatFS import PyFatFS
from p38_stage_creative_awe32_win95 import partition_offset


def variable_length(n: int) -> bytes:
    if n < 0:
        raise ValueError("negative delta time")
    chunks = [n & 0x7f]
    n >>= 7
    while n:
        chunks.append((n & 0x7f) | 0x80)
        n >>= 7
    return bytes(reversed(chunks))


def midi_fixture(program: int) -> bytes:
    if not 0 <= program <= 127:
        raise ValueError("invalid program")
    events = (
        b"\x00\xff\x51\x03\x07\xa1\x20"   # tempo = 500000 us/qn (120 BPM)
        + b"\x00\xc0" + bytes([program])  # GM program on channel 0
        + b"\x00\x90\x30\x64"             # MIDI note 48, velocity 100
        + variable_length(1920) + b"\x80\x30\x00"  # 2 s, note off
        + b"\x00\xff\x2f\x00"
    )
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480) + (
        b"MTrk" + struct.pack(">I", len(events)) + events
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--disk", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    reports = {}
    with PyFatFS(str(args.disk), offset=partition_offset(args.disk),
                 read_only=False, preserve_case=False) as fs:
        fs.makedirs("AWE32", recreate=True)
        for prog in (0, 7):
            name = f"P49-P{prog}.MID"
            raw = midi_fixture(prog)
            with fs.openbin("AWE32/" + name, "w") as f:
                f.write(raw)
            reports[name] = {"bytes": len(raw), "program": prog,
                             "channel": 1, "note": 48, "velocity": 100,
                             "duration_seconds": 2,
                             "exists_after_stage": fs.exists("AWE32/" + name)}
        for path in ("WINDOWS/MPLAYER.EXE", "WINDOWS/SYSTEM/MCISEQ.DRV",
                     "WINDOWS/SYSTEM/MIDI.DRV", "WINDOWS/WIN.INI"):
            reports[path] = bool(fs.exists(path))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(reports, indent=2)+"\n", encoding="utf8")
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
