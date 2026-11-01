#!/usr/bin/env python3
"""P37: Forensic, read-only inspection of the preinstalled Win95 image.

Read MBR + FAT directories without booting the guest, no disk redistribution.
Determines whether a compatible AWE32 Win95 INF and Creative VxD/DRV/DLL
already exist, plus a writable injection path for the original driver.
"""
from __future__ import annotations
import argparse
import json
import re
import struct
import subprocess
from pathlib import Path

CANDIDATES = {
 "root_autoexec": "::AUTOEXEC.BAT",
 "root_config": "::CONFIG.SYS",
 "windows_winini": "::WINDOWS/WIN.INI",
 "windows_systemini": "::WINDOWS/SYSTEM.INI",
 "creative_inf": "::WINDOWS/INF/SB16AWE.INF",
 "creative_vxd": "::WINDOWS/SYSTEM/SBAWE.VXD",
 "creative_drv": "::WINDOWS/SYSTEM/SBAWE32.DRV",
 "creative_manager": "::WINDOWS/SYSTEM/AWEMAN32.DLL",
 "win95_setupx": "::WINDOWS/SYSTEM/SETUPX.DLL",
 "win95_rundll": "::WINDOWS/RUNDLL.EXE",
 "win95_regedit": "::WINDOWS/REGEDIT.EXE",
}
def mtool(image, offset, command, name):
    img=f"{image}@@{offset}"
    return subprocess.run([command,"-i",img,name], capture_output=True,text=True,timeout=20)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("image",type=Path)
    p.add_argument("--output",type=Path,default=Path("P37-Win95-driver-inventory.json"))
    args=p.parse_args()
    data=args.image.open("rb").read(512)
    if data[-2:]!=b"\x55\xaa": raise SystemExit("MBR invalid")
    parts=[]
    for i in range(4):
        block=data[446+i*16:462+i*16]
        typ=block[4]
        start,n=struct.unpack_from("<II",block,8)
        if typ and n:
            parts.append({"slot":i,"type":f"0x{typ:02X}","start_lba":start,"length_sectors":n,"offset_bytes":start*512})
    if not parts: raise SystemExit("No primary MBR partitions")
    partition=next((x for x in parts if int(x["type"],16) in (0x04,0x06,0x0B,0x0C,0x0E)),None)
    if partition is None: raise SystemExit("No recognized FAT partition")
    offset=partition["offset_bytes"]
    report={"image_bytes":args.image.stat().st_size,"partition_layout":parts,
            "fat_partition_offset":offset,"driver_files":{}, "top_level":[]}
    for item,path in CANDIDATES.items():
        result=mtool(args.image,offset,"mdir",path)
        report["driver_files"][item]={
          "file":path,"found":result.returncode==0,
          "dir_listing_excerpt":result.stdout.splitlines()[-3:] if result.returncode==0 else [],
        }
    for label,path in [("root","::"),("windows_inf","::WINDOWS/INF"),("windows_system","::WINDOWS/SYSTEM")]:
        r=mtool(args.image,offset,"mdir",path)
        match=[x.strip() for x in r.stdout.splitlines()
               if re.search(r"(?i)sb16|awe|creative|synth|win|config|system|inf|regedit|run",x)]
        report["top_level"].append({"directory":label,"rc":r.returncode,"relevant_file_names":match[:45]})
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print("FAT partition:",partition)
    for k,v in report["driver_files"].items():print(f" {k}: {v['found']} ({v['file']})")
    for d in report["top_level"]:print(d["directory"],d["relevant_file_names"][:20])
    print("READ-ONLY complete; no Win95 driver was installed.")
if __name__=="__main__":main()
