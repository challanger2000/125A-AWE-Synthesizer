#!/usr/bin/env python3
"""P38: Stage matching Creative 1998 AWE32 Win95 driver files in temporary FAT16.

Original drivers downloaded only to the temporary CI runner from the published
legacy-driver mirror, verified for format and exact known filenames. No original
Creative binaries, OS disk, wave ROM or user SF2 is committed or uploaded.
Run the Windows 95 INF section through original SetupX on the guest next boot.
This does NOT by itself establish a loaded/bound VxD; verify afterwards.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import struct
import tempfile
import urllib.parse
from pathlib import Path
from urllib.request import Request,urlopen
from pyfatfs.PyFatFS import PyFatFS

SOURCE="https://sobac.com/ZIPfiles/Operating%20Systems/Windows/Drivers/Audio/SB16%20CT2940/"
FILES=[
 "sb16awe.inf","sbawe.vxd","sbawe32.drv","aweman.dll",
 "aweman32.dll","synthgm.sbk","sb16.vxd","sb16snd.drv","sbfm.drv",
 "cspman.dll","cifman.dll","cifman.crl","uidll16.dll",
 "wfm0200.acv","wfm0200a.csp","wfm0201.acv","wfm0201a.csp",
 "wfm0202.acv","wfm0202a.csp","wfm0203.acv","wfm0203a.csp"
]
EXPECTED_MAGIC={
 "sbawe.vxd":b"MZ","sbawe32.drv":b"MZ","aweman.dll":b"MZ",
 "aweman32.dll":b"MZ","sb16.vxd":b"MZ","sb16snd.drv":b"MZ",
 "uidll16.dll":b"MZ",
}
TARGETS=(
 "WINDOWS/SYSTEM/SBAWE.VXD",
 "WINDOWS/SYSTEM/SBAWE32.DRV",
 "WINDOWS/SYSTEM/AWEMAN32.DLL",
 "WINDOWS/SYSTEM/AWEMAN.DLL",
 "WINDOWS/INF/OTHER/SB16AWE.INF",
)
def partition_offset(p:Path):
    with p.open("rb") as f:sector=f.read(512)
    if sector[-2:]!=b"\x55\xaa":raise ValueError("Invalid MBR")
    for i in range(4):
        b=sector[446+16*i:462+16*i]
        start,size=struct.unpack_from("<II",b,8)
        if b[4] in (0x04,0x06,0x0b,0x0c,0x0e) and size>0:
            return start*512
    raise ValueError("Missing FAT partition")

def record_state(image:Path, report:dict):
    with PyFatFS(str(image),offset=partition_offset(image),
                 read_only=True) as fs:
        report["post_install_files"]={
            p: fs.exists(p) for p in TARGETS
        }
        registry="WINDOWS/SYSTEM.DAT"
        if fs.exists(registry):
            data=fs.readbytes(registry)
            report["registry_text_marker_counts"]={
                item:len(re.findall(item.encode(),data,re.I))
                for item in ("SBAWE","CTL0021","AWEMAN")
            }
        system="WINDOWS/SYSTEM.INI"
        if fs.exists(system):
            b=fs.readbytes(system).lower()
            report["system_ini_driver_markers"]={
                name:(name.encode() in b)
                for name in ("sbawe.vxd","sbawe32.drv","aweman32.dll")
            }
        ini=fs.readbytes("WINDOWS/WIN.INI")
        found=re.search(rb"(?im)^run=[^\r\n]*",ini)
        report["win_ini_run"]="present" if found else "absent"

def install(image:Path):
    report={
        "purpose":"Ephemeral original Creative Win95 SF2 driver staging and guest setup",
        "source":SOURCE,
        "os_disk_retained":False,
        "user_rom_tested":False,
        "user_sf2_tested":False,
        "original_vxd_running_verified":False,
        "source_files":[],
    }
    with tempfile.TemporaryDirectory(prefix="p38-creative-drivers-") as folder:
        temp=Path(folder)
        for name in FILES:
            url=SOURCE+urllib.parse.quote(name)
            data=urlopen(Request(url,headers={"User-Agent":"125A P38 creative historical-driver check"}),timeout=40).read()
            if not data or len(data)>500000:
                raise RuntimeError(f"Unexpected size for vendor file {name}: {len(data)}")
            if name in EXPECTED_MAGIC and not data.startswith(EXPECTED_MAGIC[name]):
                raise RuntimeError(f"Not a Windows vendor driver image: {name}")
            if name=="sb16awe.inf":
                s=data.decode("cp1252",errors="replace")
                for marker in ('Signature="$WINDOWS95$"','[CTL0021_Device]',
                               '[SBAWE.CopyList]','[AWEMAN.CopyList]'):
                    if marker not in s:
                        raise RuntimeError(f"Required original INF marker missing: {marker}")
            (temp/name.upper()).write_bytes(data)
            report["source_files"].append({
                "name":name.upper(),"bytes":len(data),
                "sha256":hashlib.sha256(data).hexdigest()
            })
        with PyFatFS(str(image),offset=partition_offset(image),
                     read_only=False,preserve_case=False) as fs:
            fs.makedirs("AWE32",recreate=True)
            for path in temp.iterdir():
                with fs.openbin("AWE32/"+path.name,"w") as f:
                    f.write(path.read_bytes())
            dest="WINDOWS/WIN.INI"
            original=fs.readbytes(dest)
            entry=(b'run=RUNDLL.EXE SETUPX.DLL,InstallHinfSection '
                   b'CTL0021_Device 132 C:\\AWE32\\SB16AWE.INF')
            match=re.search(rb"(?im)^run=[^\r\n]*",original)
            if not match:
                winsection=re.search(rb"(?im)^\[windows\][ \t]*\r?$",original)
                if not winsection:
                    raise ValueError("Win95 WIN.INI [windows] section absent")
                pos=winsection.end()
                modified=original[:pos]+b"\r\n"+entry+original[pos:]
            else:
                if original[match.start()+4:match.end()].strip():
                    raise RuntimeError("Refuse to replace non-empty existing WIN.INI run command")
                modified=original[:match.start()]+entry+original[match.end():]
            with fs.openbin(dest,"w") as f:f.write(modified)
            for path in FILES:
                if not fs.exists("AWE32/"+path.upper()):
                    raise RuntimeError(f"Guest driver file not written: {path}")
            report["vendor_files_staged"]=len(FILES)
            report["guest_startup_command"]=entry.decode("ascii")
    return report
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("image",type=Path)
    parser.add_argument("--phase",choices=("stage","verify"),required=True)
    parser.add_argument("--output",default="P38-Win95-install-check.json")
    args=parser.parse_args()
    if args.phase=="stage":
        result=install(args.image)
    else:
        result={"phase":"after-guest-startup","driver_bound_proven":False,
                "actual_win95_noteon_trace":False}
        record_state(args.image,result)
    result["phase"]=args.phase
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("P38",args.phase,json.dumps(result,indent=2))
    if args.phase=="verify":
        print("Registry marker and file existence are NOT proof that the VxD is loaded.")
if __name__=="__main__":main()
