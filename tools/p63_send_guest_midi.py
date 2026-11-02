#!/usr/bin/env python3
"""P63 host proof-of-transport: send short MIDI to ORIGINAL Win95 Creative WinMM.

This utility talks to 86Box's local COM1 Named Pipe; the Windows 95 guest
runs p63_win95_guest_midi.exe. It does not render audio and is NOT a VST3.
"""
from __future__ import annotations
import argparse
import os
import time
from pathlib import Path

DEFAULT_PIPE = r"\\.\pipe\125A-AWE32-MIDI"


def frame(status: int, data1: int, data2: int = 0) -> bytes:
    if not (0x80 <= status <= 0xEF) or not (0 <= data1 <= 127) or not (0 <= data2 <= 127):
        raise ValueError("Invalid MIDI channel short message")
    if status & 0xF0 in (0xC0, 0xD0) and data2:
        raise ValueError("Program change/channel pressure has no second data byte")
    return bytes((0xA5, 0x5A, status, data1, data2, status ^ data1 ^ data2 ^ 0x5A))


def demo_messages(channel: int, bank: int, program: int, note: int, velocity: int):
    if not all(0 <= v <= 127 for v in (bank, program, note, velocity)):
        raise ValueError("MIDI data out of range")
    if not 0 <= channel <= 15:
        raise ValueError("MIDI channel out of range")
    # Creative SF2 user-bank selection (often CC0=1); not interpreted in host.
    yield frame(0xB0 | channel, 0, bank)
    yield frame(0xC0 | channel, program)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pipe", default=DEFAULT_PIPE, help="86Box Windows serial Named Pipe")
    p.add_argument("--channel", type=int, default=0, help="0-based MIDI channel")
    p.add_argument("--bank", type=int, default=1)
    p.add_argument("--program", type=int, default=7)
    p.add_argument("--note", type=int, default=50, help="MIDI 50 = D3 with C4=60")
    p.add_argument("--velocity", type=int, default=100)
    p.add_argument("--hold-ms", type=int, default=500)
    p.add_argument("--dry-run", type=Path, help="Write test frames to a file, do not contact 86Box")
    a = p.parse_args()
    if a.hold_ms < 0 or a.hold_ms > 30000:
        p.error("hold-ms must be in [0, 30000]")
    init = tuple(demo_messages(a.channel, a.bank, a.program, a.note, a.velocity))
    on = frame(0x90 | a.channel, a.note, a.velocity)
    off = frame(0x80 | a.channel, a.note, 0)
    if a.dry_run:
        a.dry_run.write_bytes(b"".join((*init, on, off)))
        print("Wrote original-driver MIDI protocol fixture; NO guest/hardware execution.")
        return
    if os.name != "nt":
        p.error("Named Pipe client requires Windows; --dry-run works everywhere")
    with open(a.pipe, "wb", buffering=0) as output:
        for data in (*init, on):
            output.write(data)
        output.flush()
        time.sleep(a.hold_ms / 1000.0)
        output.write(off)
        output.flush()
    print("Forwarded MIDI to COM1 pipe; driver execution and audio NOT verified.")


if __name__ == "__main__":
    main()
