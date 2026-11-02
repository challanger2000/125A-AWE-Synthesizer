#!/usr/bin/env python3
"""P76: export *genuinely captured* 86Box/Creative Win95 bass WAVs.

Never synthesize, transform, or approximate an SF2 preset. This script reads
two existing 86Box automation WAV files, verifies they contain 44.1kHz stereo
16-bit PCM with nonzero signal, and copies them only to a caller-selected
PRIVATE local directory. Never invoke on GitHub public upload-artifact paths.
"""
from __future__ import annotations

import array
import json
import shutil
import struct
import sys
import wave
from pathlib import Path

CAPTURE_DIRS = {
    0: ("p64-private-original-creative-wavetable",
        "125A-AWE-Original-Grungy-Ramp-Bass.wav"),
    7: ("p75-private-program7",
        "125A-AWE-Original-TX81Z-Lately-Bass.wav"),
}

def pcm_stats(wav_path: Path) -> dict:
    with wave.open(str(wav_path), "rb") as file:
        channels=file.getnchannels()
        sample_width=file.getsampwidth()
        rate=file.getframerate()
        frames=file.getnframes()
        format_name=file.getcomptype()
        if (channels,sample_width,rate,format_name)!=(2,2,44100,"NONE"):
            raise ValueError(
                f"Expected real EMU8000 44.1 kHz stereo 16bit PCM: "
                f"{wav_path.name}: {channels}ch {sample_width * 8}bit "
                f"{rate}Hz {format_name}")
        if frames<22050:
            raise ValueError(f"EMU8000 private WAV too short: {frames} frames")
        nonzero=0
        while True:
            chunk=file.readframes(32768)
            if not chunk:
                break
            values=array.array("h")
            values.frombytes(chunk)
            if sys.byteorder!="little":
                values.byteswap()
            for i in range(0,len(values),2):
                if values[i] or values[i+1]:
                    nonzero+=1
        if not nonzero:
            raise ValueError(f"Silent original Creative capture: {wav_path.name}")
        return {"rate_hz":rate,"channels":channels,"bits":16,
                "frames":frames,"nonzero_frames":nonzero}

def export(original_test_dir: Path, destination: Path,
           original_trial_report: dict) -> dict:
    trial=original_trial_report.get("p64_original_win95_midi",{})
    if not trial.get("p75_original_private_sf2_test"):
        raise ValueError("P75 ORIGINAL PRIVATE SF2 test was not executed")
    if not original_trial_report.get("p75_private_sample_upload_plausible",False):
        raise ValueError("Original Creative user SF2 sample upload NOT established; GM fallback cannot be exported as an original bass")
    if trial.get("original_creative_midi_activity_register_write_delta",0)<=0:
        raise ValueError("Original Creative EMU8000 MIDI did not change registers")
    original=trial.get("p75_program_results",[])
    if [x.get("program") for x in original]!=[0,7]:
        raise ValueError("Missing exact MIDI programs 0 and 7 in original Creative test")
    if any(not x.get("nonzero_audio") for x in original):
        raise ValueError("One of the private basses is silent or not verified")
    found=[]
    for program,(folder,filename) in CAPTURE_DIRS.items():
        subdir=original_test_dir/folder
        matches=sorted(p for p in subdir.glob("*.wav")
                       if "wavetable" in p.name.lower())
        if len(matches)!=1:
            raise FileNotFoundError(
                f"Expected exactly one original Creative wavetable WAV "
                f"for MIDI program {program}; found {len(matches)}")
        stats=pcm_stats(matches[0])
        found.append((program,matches[0],filename,stats))
    # Fail-closed before modifying the requested private destination.
    destination.mkdir(parents=True,exist_ok=True)
    result=[]
    for program,source,filename,stats in found:
        target=destination/filename
        if source.resolve()==target.resolve():
            raise ValueError("Input and private destination cannot coincide")
        shutil.copyfile(source,target)
        if target.stat().st_size!=source.stat().st_size:
            raise IOError("Private Creative WAV export length mismatch")
        result.append({"midi_program":program,"wav":str(target),
                       **stats,"not_physical_hardware_comparison":True})
    return {"phase":"P76","rendering":"original Win95 Creative AWE WinMM / EMU8000 in 86Box",
            "original_private_sf2_exercised":True,
            "private_local_exports":result,
            "user_audio_uploaded_publicly":False}
