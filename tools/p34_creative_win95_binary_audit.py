#!/usr/bin/env python3
"""P34: Inspect Creative's *original* Win95 AWE32 manager and driver binaries.

Downloads into an ephemeral tempfile; verifies exact git-blob hashes and
records architecture/entrypoints/imports/format markers, NOT copyrighted
binary payloads. No VM is run, and no SF2 conversion parity is claimed.
"""
from __future__ import annotations
import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.request import urlopen, Request

import pefile

ROOT = "https://raw.githubusercontent.com/qb40/sound-blaster-awe32/master/"
FILES = {
    "manager": ("WINDOWS/DLL/AWEMAN32.DLL",
                "96123ca4c83cd41a760a66cf0652f0595f694ae7"),
    "vxd": ("WINDOWS/DRV/WIN95/SBAWE.VXD",
            "88d82c9c0ef1629fb61f1a011a762e2b6298d2e5"),
    "multimedia": ("WINDOWS/DRV/WIN95/SBAWE32.DRV",
                   "b58edbba2c1dcfef1aa63937d419dd33133872fb"),
}
INTEREST = (
    "sfbk", "sf2", "sfnt", ".sbk", ".sf2", "soundfont", "preset",
    "gen", "instrument", "ifil", "phdr", "pbag", "pgen", "igen",
    "riff", "LIST", "SBAWE", "AWE", "bank", "sample", "wav"
)
# Count and list *distinct* technical markers only; do not emit binary bytes
# or dump strings that might be copyrighted prose.
def markers(buf: bytes) -> list[dict]:
    found = []
    for keyword in INTEREST:
        pattern = re.compile(re.escape(keyword.encode()), flags=re.IGNORECASE)
        locations = [m.start() for m in pattern.finditer(buf)]
        if locations:
            found.append({"token": keyword, "count": len(locations),
                          "offsets": locations[:8]})
    return found

def git_blob_sha(buf: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(buf)).encode() + b"\0" + buf).hexdigest()

def inspect_pe(data: bytes):
    try:
        p = pefile.PE(data=data, fast_load=False)
    except pefile.PEFormatError:
        return {"pe_valid": False}
    exports = []
    if hasattr(p, "DIRECTORY_ENTRY_EXPORT"):
        for sym in p.DIRECTORY_ENTRY_EXPORT.symbols:
            exports.append(sym.name.decode("latin1") if sym.name else f"ordinal_{sym.ordinal}")
    imports = {}
    if hasattr(p, "DIRECTORY_ENTRY_IMPORT"):
        for lib in p.DIRECTORY_ENTRY_IMPORT:
            imports[lib.dll.decode("latin1")] = [
                e.name.decode("latin1") if e.name else f"ordinal_{e.ordinal}"
                for e in lib.imports
            ]
    return {
        "pe_valid": True, "machine": hex(p.FILE_HEADER.Machine),
        "subsystem": p.OPTIONAL_HEADER.Subsystem,
        "entry_rva": hex(p.OPTIONAL_HEADER.AddressOfEntryPoint),
        "export_count": len(exports), "exports": exports[:80],
        "imports": {key: value[:70] for key, value in imports.items()},
    }

def inspect_executable(data: bytes):
    if data[:2] != b"MZ":
        return "NOT_MZ"
    if len(data) < 0x40:
        return "TRUNCATED_MZ"
    ofs = int.from_bytes(data[0x3c:0x40], "little")
    return data[ofs:ofs+4].decode("latin1", errors="replace")

def main():
    record = {
        "purpose": "Identify original 1996 Windows-95 AWE32 SF2 load/driver components",
        "source": "Creative ADIP3.01 mirror; exact git hashes validated",
        "private_sf2_tested": False,
        "win95_guest_executed": False,
        "actual_original_note_on_trace": False,
        "full_register_parity_proven": False,
        "components": {}
    }
    with tempfile.TemporaryDirectory(prefix="creative-original-p34-") as folder:
        for name, (path, expected_sha) in FILES.items():
            req = Request(ROOT + path, headers={"User-Agent":"125A-research-p34"})
            data = urlopen(req, timeout=45).read()
            actual = git_blob_sha(data)
            if actual != expected_sha:
                raise RuntimeError(f"{path}: original hash mismatch: {actual}")
            item = {
                "original_path": path,
                "size": len(data),
                "verified_git_blob_sha": actual,
                "executable_type_signature": inspect_executable(data),
                "technical_marker_counts": markers(data),
                **inspect_pe(data)
            }
            record["components"][name] = item
        # Validate and cite Creative's *published sample application's* call
        # route, without deriving its source into a commercial project.
        source_path="WINDOWS/SAMPLE/AWEDEMO/WINAWE32.C"
        req=Request(ROOT+source_path,headers={"User-Agent":"125A-research-p34"})
        sample=urlopen(req,timeout=45).read()
        if git_blob_sha(sample)!="a6b3986478ec739a3cd13f7baadee8c1d61dec4":
            raise RuntimeError("Sample program hash changed")
        calls=["AWEMAN32.DLL","AWE_LOAD_USER_BANK","AWE_SEND_MIDI"]
        source=sample.decode("latin1")
        if not all(x in source for x in calls):
            raise RuntimeError("Original sample manager call path not found")
        record["manager_sample_call_route_verified"]=calls
    Path("P34-Creative-Win95-original-binary-audit.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False)+"\n", encoding="utf8")
    for name, item in record["components"].items():
        print(name, item["original_path"], "size", item["size"],
              "format", repr(item["executable_type_signature"]),
              "PE", item["pe_valid"],
              "export_count", item.get("export_count"),
              "markers", [m["token"] for m in item["technical_marker_counts"]])
        if item.get("exports"):
            print("  exports:", item["exports"])
        if item.get("imports"):
            print("  import DLLs:", list(item["imports"]))
    print("VERIFIED: original Creative Windows API sample -> AWEMAN32 manager "
          "AWE_LOAD_USER_BANK + AWE_SEND_MIDI.")
    print("NOT VERIFIED: VXD's exact SoundFont2 generator semantics; no guest "
          "or Win95 register trace executed.")
if __name__ == "__main__":
    main()
