#!/usr/bin/env python3
"""Private lab test ONLY: auto-play programs 0 and 7 in original Creative DOS demo.

Requires an independently acquired DEMO.EXE (Creative ADIP 3.01). Do not
distribute the input, patched output, ROM or SoundFonts with the VST3.
"""
import argparse
import hashlib
from pathlib import Path

EXPECTED_HASH = "49bcb8ad27ba24bf021b7697a924595da8846666a218a8b56440dff2207db647"
CHECKS = {
    0x1469: "9a3821ed05",  # kbhit
    0x1472: "9a5e21ed05",  # getch
    0x1490: "56",          # push extra-WAV bank
    0x149a: "33c951",      # push program zero
    0x14a6: "b83c00",      # MIDI note 60
    0x14aa: "b87f00",      # velocity 127
    0x14b3: "8b16460042",  # original MPU poll
}

def instrument(original: bytes, program: int, note=48, velocity=100) -> bytes:
    if len(original) != 40197 or hashlib.sha256(original).hexdigest() != EXPECTED_HASH:
        raise ValueError("Original Creative ADIP 3.01 DEMO.EXE SHA256 mismatch")
    if program not in (0, 7) or not (0 <= note <= 127 and 1 <= velocity <= 127):
        raise ValueError("Unsupported program or MIDI event")
    for pos, pattern in CHECKS.items():
        expected = bytes.fromhex(pattern)
        if original[pos:pos+len(expected)] != expected:
            raise ValueError("Mismatched opcode at file offset " + hex(pos))
    b=bytearray(original)
    b[0x1469:0x146e] = bytes.fromhex("b801009090") # kbhit = true
    b[0x1472:0x1477] = bytes.fromhex("b831009090") # getch = '1'
    b[0x1490] = 0x51 # bank index 0, not extra-WAV index 1
    if program == 7:
        b[0x149a:0x149d] = bytes.fromhex("6a0790") # push program 7
    b[0x14a7] = note
    b[0x14ab] = velocity
    # BIOS int15 AH86 waits ~2s; follow normal app cleanup.
    code = bytes.fromhex("b486b91e00ba8084cd15eb0d")
    b[0x14b3:0x14cc] = code+b"\x90"*(0x14cc-0x14b3-len(code))
    if len(b) != len(original):
        raise AssertionError("Image length changed")
    return bytes(b)

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--original-exe",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    raw=args.original_exe.read_bytes()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for program in (0,7):
        b=instrument(raw,program)
        path=args.output_dir / ("DEMO%d.EXE" % program)
        path.write_bytes(b)
        print(path,hashlib.sha256(b).hexdigest(),"PRIVATE/DO NOT DISTRIBUTE")
