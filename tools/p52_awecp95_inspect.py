#!/usr/bin/env python3
"""P52: provenance/structure inspection of original Creative AWECP95 2.05 SFX.

AWECP95 package and its extracted files remain ONLY on the disposable
GitHub Actions runner. The public artifact contains only filename/size metadata
(no archive bytes, ROMs, guest OS, SF2, Windows 95 driver or sample audio).
Do not report installation as tested from this probe alone.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

def parse_7z_slt(stdout: str) -> list[dict]:
    entries = []
    current = {}
    for line in stdout.splitlines():
        if line.startswith("Path = "):
            if current.get("name"):
                entries.append(current)
            current = {"name":line[7:].strip()}
        elif line.startswith("Size = ") and current:
            try: current["bytes"] = int(line[7:].strip())
            except ValueError: pass
        elif line.startswith("Attributes = ") and current:
            current["attributes"] = line[13:].strip()
    if current.get("name"):
        entries.append(current)
    # 7z includes a top-level container entry; ignore it if it is an archive.
    return [x for x in entries if x.get("name","").lower() not in
            {"awecp95.exe","awecp95"}]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    binary = args.exe.read_bytes()
    report = {
        "phase": "P52",
        "package": "Creative AWE Control Panel for Windows 95 v2.05",
        "source": "Phil's Computer Lab historical Creative mirror; original filename AWECP95.EXE",
        "download_size": len(binary),
        "sha256": hashlib.sha256(binary).hexdigest(),
        "dos_mz_header": binary[:2] == b"MZ",
        "is_public_binary_artifact": False,
        "windows95_install_executed": False,
        "original_user_sf2_loaded": False,
        "sf2_support_documented_by_creative": True,
    }
    listing = subprocess.run(
        ["7z","l","-slt",str(args.exe)],capture_output=True,text=True,
        errors="replace",timeout=45)
    report["7zip_exit_code"] = listing.returncode
    report["archive_entries"] = parse_7z_slt(listing.stdout)[:160]
    report["archive_entry_count"] = len(report["archive_entries"])
    if listing.returncode != 0:
        report["7zip_stderr"] = listing.stderr[-1500:]
    report["likely_setup_files"] = [
        x["name"] for x in report["archive_entries"]
        if re.search(r"awecp|setup|install|readme",x["name"],re.I)
    ]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print(json.dumps(report,indent=2))
    if len(binary) < 150_000 or len(binary) > 250_000 or not report["dos_mz_header"]:
        raise AssertionError("Creative AWECP95 historical package looks invalid")

if __name__=="__main__":
    main()
