#!/usr/bin/env python3
"""P53: privately stage original AWE Control Panel 2.05 to disposable Win95 disk.

Only executable/resource files extracted from a separately obtained original
Creative AWECP95 package are copied. No payload is committed or uploaded as
an Actions artifact. Start application by its path; this is not yet proof
that a custom SoundFont is loaded.
"""
import argparse
import hashlib
import json
from pathlib import Path
from pyfatfs.PyFatFS import PyFatFS
from p38_stage_creative_awe32_win95 import partition_offset

NAMES=("AWECP32.EXE","AWE32RES.DLL","AWECP.HLP","AWECP.CNT","README.TXT")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--disk",type=Path,required=True)
    p.add_argument("--files",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    report={"phase":"P53","control_panel":"Creative AWE Control Panel 2.05",
            "guest_path":"C:\\AWE32\\CP\\AWECP32.EXE",
            "sf2_loaded":False,"windows95_app_open_verified":False,
            "binaries_retained_in_artifacts":False,"files":[]}
    with PyFatFS(str(a.disk),offset=partition_offset(a.disk),
                 read_only=False,preserve_case=False) as fs:
        fs.makedirs("AWE32/CP",recreate=True)
        for name in NAMES:
            source=a.files/name
            if not source.is_file():
                if name in ("AWECP.HLP","AWECP.CNT","README.TXT"):
                    continue
                raise FileNotFoundError(source)
            raw=source.read_bytes()
            if not raw or len(raw)>2_000_000:
                raise ValueError("Unexpected Creative package member size")
            if name.endswith((".EXE",".DLL")) and raw[:2]!=b"MZ":
                raise ValueError(f"Invalid Windows executable {name}")
            with fs.openbin("AWE32/CP/"+name,"w") as f:
                f.write(raw)
            report["files"].append({"name":name,"bytes":len(raw),
                                    "sha256":hashlib.sha256(raw).hexdigest()})
        if not fs.exists("AWE32/CP/AWECP32.EXE") or not fs.exists("AWE32/CP/AWE32RES.DLL"):
            raise AssertionError("AWE Control Panel executable and DLL missing")
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
