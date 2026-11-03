#!/usr/bin/env python3
"""P84: export private, real Creative Win95 EMU8000 program audition WAVs.

Unlike P76, these WAV names use the actual selected SF2 bank/program/name,
not the two legacy TX81Z bass names. Only copies existing 86Box wavetable PCM.
"""
from __future__ import annotations
import re
import shutil
from pathlib import Path
from p76_export_private_wav import pcm_stats

def safe_name(name):
    value=re.sub(r"[^A-Za-z0-9._ -]+","_",str(name)).strip(" ._-")
    return value[:42] or "Unnamed"

def export(out,private_destination,report):
    if not report.get("p84_universal_sf2_test"):
        raise ValueError("Not a universal SF2 test")
    if not report.get("p75_private_sample_upload_plausible"):
        raise ValueError("The original Creative driver SF2 upload is unverified")
    expected=report.get("p84_selected_presets",[])
    if len(expected)!=2:
        raise ValueError("The audition must contain exactly two presets")
    actual=report.get("p64_original_win95_midi",{}).get("p75_program_results",[])
    if len(actual)!=2 or [p.get("program") for p in actual]!=[p["program"] for p in expected]:
        raise ValueError("The measured MIDI programs differ from requested SF2 programs")
    if not all(x.get("nonzero_audio") for x in actual):
        raise ValueError("One or more original Creative programs produced no audio")
    folders=["p64-private-original-creative-wavetable","p75-private-program7"]
    copies=[]
    for ix,(preset,folder) in enumerate(zip(expected,folders)):
        wavs=sorted((Path(out)/folder).glob("*wavetable*.wav"))
        if len(wavs)!=1:
            raise FileNotFoundError("No unambiguous original EMU8000 WAV for program %d"%preset["program"])
        stats=pcm_stats(wavs[0])
        repeated=expected[0]["bank"]==expected[1]["bank"] and expected[0]["program"]==expected[1]["program"]
        suffix=("-Take%d"%(ix+1)) if repeated else ""
        filename=("125A-AWE-UserBank%03d-SF2Bank%03d-P%03d-%s%s.wav"
                  %(report["p84_creative_user_bank"],preset["bank"],
                    preset["program"],safe_name(preset["name"]),suffix))
        copies.append((wavs[0],filename,stats,preset))
    dest=Path(private_destination)
    dest.mkdir(parents=True,exist_ok=True)
    files=[]
    for original,filename,stats,preset in copies:
        target=dest/filename
        if target.resolve()==original.resolve():
            raise ValueError("Source and destination must differ")
        shutil.copyfile(original,target)
        if target.stat().st_size!=original.stat().st_size:
            raise IOError("Original capture file copy was truncated")
        files.append({"path":str(target),"preset":preset,**stats})
    return {"phase":"P84","original_creative_win95_audio":True,
            "private_wavs":files,"soundfont_pcm_substituted":False}
