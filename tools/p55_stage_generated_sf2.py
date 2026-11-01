#!/usr/bin/env python3
"""P55: create a tiny ORIGINAL laboratory SF2 and stage on disposable Win95 disk.

All PCM is programmatically generated sine; no user bank or Creative data
is embedded, redistributed or published. The original Creative Win95
Control Panel will be used to attempt a USER SoundFont bank load.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from pyfatfs.PyFatFS import PyFatFS
from p38_stage_creative_awe32_win95 import partition_offset


def chunk(tag: bytes, value: bytes) -> bytes:
    assert len(tag) == 4
    return tag + struct.pack("<I", len(value)) + value + (b"\0" if len(value) % 2 else b"")


def list_chunk(tag: bytes, *chunks: bytes) -> bytes:
    return chunk(b"LIST", tag + b"".join(chunks))


def name20(name: str) -> bytes:
    raw = name.encode("ascii")
    assert len(raw) < 20
    return raw.ljust(20, b"\0")


def make_sf2() -> bytes:
    frames = 4410
    pcm = [int(round(11500 * math.sin(2 * math.pi * 440 * i / 44100)))
           for i in range(frames)]
    data = struct.pack("<" + "h" * frames, *pcm) + b"\0" * (46 * 2)
    info = list_chunk(b"INFO",
        chunk(b"ifil", struct.pack("<HH", 2, 1)),
        chunk(b"isng", b"EMU8000\0"),
        chunk(b"INAM", b"125A P55 Laboratory Sine Bank\0"),
        chunk(b"ICMT", b"Original synthetic sine, no third-party content\0"))
    sdta = list_chunk(b"sdta", chunk(b"smpl", data))
    # Exactly one bank0/program0 preset, one instrument, one mono sample.
    phdr = (
        name20("P55 Sine Tone") + struct.pack("<HHHIII", 0, 0, 0, 0, 0, 0)
        + name20("EOP") + struct.pack("<HHHIII", 0, 0, 1, 0, 0, 0)
    )
    pbag = struct.pack("<HHHH", 0, 0, 1, 0)
    pmod = bytes(10)
    pgen = struct.pack("<HHHH", 41, 0, 0, 0)  # instrument 0, terminal
    inst = name20("P55 Sine") + struct.pack("<H", 0) + name20("EOI") + struct.pack("<H", 1)
    ibag = struct.pack("<HHHH", 0, 0, 2, 0)
    imod = bytes(10)
    igen = struct.pack("<HHHHHH", 54, 1, 53, 0, 0, 0) # looping sample0, terminal
    shdr = (name20("P55 Sine 440")
            + struct.pack("<IIIIIbbHH", 0, frames, 200, frames - 200,
                          44100, 69, 0, 0, 1)
            + name20("EOS")
            + struct.pack("<IIIIIbbHH", frames + 46, frames + 46, frames + 46,
                          frames + 46, 44100, 0, 0, 0, 1))
    pdta = list_chunk(b"pdta",
        chunk(b"phdr", phdr), chunk(b"pbag", pbag),
        chunk(b"pmod", pmod), chunk(b"pgen", pgen),
        chunk(b"inst", inst), chunk(b"ibag", ibag),
        chunk(b"imod", imod), chunk(b"igen", igen),
        chunk(b"shdr", shdr))
    raw = b"sfbk" + info + sdta + pdta
    return b"RIFF" + struct.pack("<I", len(raw)) + raw


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--disk", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    sf2 = make_sf2()
    if not sf2.startswith(b"RIFF") or sf2[8:12] != b"sfbk":
        raise AssertionError("Invalid SF2 RIFF form")
    with PyFatFS(str(a.disk), offset=partition_offset(a.disk),
                 read_only=False, preserve_case=False) as fs:
        fs.makedirs("AWE32", recreate=True)
        with fs.openbin("AWE32/P55TEST.SF2", "w") as f:
            f.write(sf2)
        if fs.readbytes("AWE32/P55TEST.SF2") != sf2:
            raise AssertionError("Guest FAT stored a different P55 test SF2")
    report = {
        "phase": "P55", "file": "C:\\AWE32\\P55TEST.SF2",
        "size_bytes": len(sf2), "sha256": hashlib.sha256(sf2).hexdigest(),
        "preset": "P55 Sine Tone", "bank": 0, "program": 0,
        "waveform": "generated 440 Hz sine", "samples": 1,
        "original_creative_bank_load_verified": False,
        "user_original_synth512_bank_present": False,
        "original_user_soundfont_bytes_uploaded": False}
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, indent=2)+"\n", encoding="utf8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
