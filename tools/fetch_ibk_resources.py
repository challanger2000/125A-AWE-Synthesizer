#!/usr/bin/env python3
"""Fetch and verify the two MIT-licensed historical FM factory banks for build packaging.

At development/build time ONLY. No internet connection or IBK files are required
at plugin runtime. Source bytes are pinned and match the owner's IBK.ZIP exactly.
"""
from pathlib import Path
import hashlib
import sys
from urllib.request import urlopen

BASE = ("https://raw.githubusercontent.com/Wohlstand/libADLMIDI/"
        "3e9ddb13ad39e2de0ca7eb003e622d4741aa50b7/"
        "fm_banks/ibk_files/ibk/")
FILES = {
    "MAUIFM.IBK": "361e9967a1677c6ae1b04373b2a8eed6cdb3c2ae662ad2d7e8737273032c419b",
    "DRUM.IBK":   "74b39496668c6a85c5742f57f7afa97fefb4bff45e8e9c67661c3f2db77a2f9c",
}
LICENSE_GIT_BLOB = "69272b01a7b37485368754bea597c720c9301232"

def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

def verified(name, data):
    if name.endswith(".IBK"):
        if len(data) != 3204 or data[:4] != b"IBK\x1a":
            raise ValueError("Invalid IBK format: " + name)
        if hashlib.sha256(data).hexdigest() != FILES[name]:
            raise ValueError("Wrong historical IBK content: " + name)
    elif git_blob(data) != LICENSE_GIT_BLOB:
        raise ValueError("License source unexpectedly changed")

def main(dst):
    dst.mkdir(parents=True, exist_ok=True)
    for name in (*FILES, "IBK_License.txt"):
        path = dst / name
        existing = path.read_bytes() if path.is_file() else None
        if existing is not None:
            try:
                verified(name, existing)
                print("IBK cache verified:", name)
                continue
            except ValueError:
                pass
        with urlopen(BASE + name, timeout=30) as response:
            data = response.read(8192)
        verified(name, data)
        path.write_bytes(data)
        print("IBK source verified:", name)
    print("P15 historical FM bank packaging: PASS")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: fetch_ibk_resources.py OUTPUT_RESOURCE_DIR")
    main(Path(sys.argv[1]))
