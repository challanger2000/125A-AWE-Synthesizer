#!/usr/bin/env python3
"""Validate actual built VST3 assets; a compile alone is insufficient."""
from pathlib import Path
import hashlib
import sys

EXPECTED = {
    "MAUIFM.IBK": "361e9967a1677c6ae1b04373b2a8eed6cdb3c2ae662ad2d7e8737273032c419b",
    "DRUM.IBK": "74b39496668c6a85c5742f57f7afa97fefb4bff45e8e9c67661c3f2db77a2f9c",
}
root=Path(sys.argv[1])
assert root.is_dir(), f"Missing VST3 Resources: {root}"
for name,sha in EXPECTED.items():
    content=(root/name).read_bytes()
    assert len(content)==3204 and content[:4]==b"IBK\x1a"
    assert hashlib.sha256(content).hexdigest()==sha, name
    print("PASS: packaged",name)
melodic=(root/"MAUIFM.IBK").read_bytes()
patches=[melodic[4+i*16:4+(i+1)*16] for i in range(128)]
assert len(set(patches))==128, "MAUIFM does not contain 128 distinct instruments"
drum=(root/"DRUM.IBK").read_bytes()
for note,kind in [(35,6),(38,7),(45,8),(49,9),(42,10)]:
    assert drum[4+16*note+11]==kind, f"wrong MIDI percussion mapping {note}"
license=(root/"IBK_License.txt").read_bytes()
assert b"MIT License" in license and b"Jamie" in license
print("P15 PASS: 128 melodic programs, five OPL3 percussion types, MIT license shipped")
