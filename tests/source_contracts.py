#!/usr/bin/env python3
"""Static audit-presence and copyrighted-asset exclusion check. NOT an audio test."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
upstream = root / "upstream" / "AWE32Emu"
required = [
    "CMakeLists.txt",
    "AWE32Emu/src/86box/snd_emu8k.c",
    "AWE32Emu/src/86box/include/86box/snd_emu8k.h",
    "AWE32Emu/src/Emu8000.cpp",
    "AWE32Emu/src/Emu8000Box.cpp",
    "AWE32Emu/src/SoundFont.cpp",
    "AWE32Emu/src/Synth.cpp",
    "AWE32Emu/src/main.cpp",
    "COPYING.GPL-2.0",
]
missing = [name for name in required if not (upstream / name).is_file()]
assert not missing, "Incomplete upstream source baseline: " + ", ".join(missing)

forbidden = {".raw", ".rom", ".sf2", ".sbk", ".sfz", ".mdi", ".vxd", ".drv", ".wav", ".iso", ".hfe", ".img"}
found = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.suffix.lower() in forbidden and ".git" not in p.parts]
assert not found, "Protected binary/audio resources in source tree: " + ", ".join(found)
print("PASS: upstream source presence and protected binary-asset exclusion ONLY")
print("NOT RUN: compile, MIDI, audio, ROM, VST3 and Studio One checks")
