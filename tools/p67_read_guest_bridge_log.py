#!/usr/bin/env python3
"""P67 strict end-to-end Win95 guest Creative MIDI evidence gate.

Reads only P63LOG.TXT from the disposable Win95 FAT image AFTER 86Box exits.
Never exports Win95, Creative binaries, ROMs, private user SF2 or MIDI traces.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from pyfatfs.PyFatFS import PyFatFS
from p38_stage_creative_awe32_win95 import partition_offset


def inspect(log: bytes) -> dict:
    if len(log)>8192:
        raise ValueError("Unexpected Win95 agent diagnostic size")
    txt=log.decode("ascii","replace")
    return {
        "phase":"P67",
        "agent_launched_in_actual_win95":"P66 CRT-free original Creative Win95 bridge startup" in txt,
        "original_creative_winmm_endpoint_selected":"SELECTED original Creative AWE Synth" in txt,
        "original_creative_com1_ready":"READY COM1 115200 8N1" in txt,
        "creatives_midi_short_messages_delivered":txt.count("MIDI DELIVERED"),
        "win95_agent_error":any(line.startswith("ERROR ") for line in txt.splitlines()),
        "private_driver_executable_logged":False,
        "raw_user_sf2_published":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--disk",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    with PyFatFS(str(a.disk),offset=partition_offset(a.disk),read_only=True,preserve_case=False) as fs:
        if fs.exists("AWE32/P63LOG.TXT"):
            result=inspect(fs.readbytes("AWE32/P63LOG.TXT"))
        else:
            result={"phase":"P67","agent_launched_in_actual_win95":False,
                    "original_creative_winmm_endpoint_selected":False,
                    "original_creative_com1_ready":False,
                    "creatives_midi_short_messages_delivered":0,
                    "win95_agent_error":True,
                    "raw_user_sf2_published":False,
                    "error":"Win95 guest agent never created P63LOG.TXT"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps(result,indent=2))
    ok=(result["agent_launched_in_actual_win95"]
        and result["original_creative_winmm_endpoint_selected"]
        and result["original_creative_com1_ready"]
        and result["creatives_midi_short_messages_delivered"]>=4
        and not result["win95_agent_error"])
    if not ok:
        raise SystemExit("P67 FAIL: original Win95 Creative WinMM MIDI path is not proven")


if __name__=="__main__":
    main()
