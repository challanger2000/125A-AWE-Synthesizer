#!/usr/bin/env python3
"""P72 fail-closed Windows 95 PE32 entrypoint check.

A successful cross-compiler return code does not prove that GNU ld resolved
'-e' for a __stdcall WINAPI entry. An unresolved undecorated symbol silently
defaulted both EXEs to the start of .text, executing internal helpers instead
of the actual Win95 entrypoints. Compare PE OptionalHeader.AddressOfEntryPoint
against the linked COFF symbol VMA, using only standard-library tools.
"""
from __future__ import annotations
import argparse
import re
import struct
import subprocess
from pathlib import Path

def pe_entry_vma(path: Path) -> int:
    data = path.read_bytes()
    if len(data) < 256 or data[:2] != b"MZ":
        raise ValueError("not an MZ executable")
    peoff, = struct.unpack_from("<I", data, 0x3C)
    if peoff + 64 > len(data) or data[peoff:peoff+4] != b"PE\x00\x00":
        raise ValueError("not a PE executable")
    optional = peoff + 24
    magic, = struct.unpack_from("<H", data, optional)
    if magic != 0x10b:
        raise ValueError("Windows 95 must receive a 32-bit PE32 executable")
    entry_rva, = struct.unpack_from("<I", data, optional+16)
    image_base, = struct.unpack_from("<I", data, optional+28)
    if not entry_rva:
        raise ValueError("PE32 has no entrypoint")
    return image_base+entry_rva

def nm_symbol_vma(output: str, symbol: str) -> int:
    escaped=re.escape(symbol)
    hits=re.findall(r"^([0-9a-fA-F]{8,16})\s+[Tt]\s+"+escaped+r"$",
                    output,re.MULTILINE)
    if len(hits) != 1:
        raise ValueError(f"Expected one defined code symbol {symbol!r}, found {hits}")
    return int(hits[0],16)

def verify(path: Path, symbol: str, nm: str) -> dict:
    entry=pe_entry_vma(path)
    result=subprocess.run([nm,"-n",str(path)],capture_output=True,
                          text=True,check=True)
    target=nm_symbol_vma(result.stdout,symbol)
    if entry!=target:
        raise AssertionError(
            f"{path.name}: WRONG ENTRY PE=0x{entry:08X} "
            f"actual {symbol}=0x{target:08X}. Link with -Wl,-e,{symbol}.")
    return {"exe":path.name,"entry_symbol":symbol,
            "entry_vma":f"0x{entry:08X}","pass":True}

def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("exe",type=Path)
    ap.add_argument("entry_symbol")
    ap.add_argument("--nm",default="i686-w64-mingw32-nm")
    a=ap.parse_args()
    print(verify(a.exe,a.entry_symbol,a.nm))
if __name__=="__main__":
    main()
