#!/usr/bin/env python3
"""P220 bind 154 actual Windows VST3 process() WAVs to verified SF2, DLL, MIDI.

This is a receipt builder, NOT an audio synthesizer, and it does not
impersonate the original Creative driver. All files remain private.
A synthetic two-case Windows host probe is ALWAYS rejected here.
"""
from __future__ import annotations
import argparse, hashlib, json, re, struct, wave
from pathlib import Path
from p220_77_preset_capture_plan import BANK_SHA,plan as generate_plan

SHA=re.compile(r"^[0-9a-f]{64}$")
LINE=re.compile(
 r"^P220_VST3_PCM (P(\d{3})-(DRY|MODFX)) program=(\d+) "
 r"note=(\d+) velocity=(\d+) frames=(\d+) callbacks=(\d+) "
 r"rms=([0-9.eE+\-]+) peak=([0-9.eE+\-]+) private_wav=YES$")
MODE="P220_MODE=OWNER_PRIVATE_77_VST3_RECORDINGS_NOT_CREATIVE ACTUAL_VST3_AUDIO_PAIRS=154 ACTUAL_CREATIVE_DRIVER_RUN=NO"
def require(ok,msg):
    if not ok:raise ValueError("P220 actual Windows VST3 receipt invalid: "+msg)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for blob in iter(lambda:f.read(1024*1024),b""):h.update(blob)
    return h.hexdigest()
def assemble(sf2,rom,module,contract,log,wavdir,exe):
    sf2,rom,module,contract,log,wavdir,exe=map(
        Path,(sf2,rom,module,contract,log,wavdir,exe))
    require(sf2.is_file() and sf2.stat().st_size==555754 and sha(sf2)==BANK_SHA,
            "wrong original 77 program owner SF2")
    require(rom.is_file() and rom.stat().st_size==1048576,
            "missing actual Wave-ROM file")
    require(module.is_file() and exe.is_file(),
            "missing real Windows DLL or verified independent VST3 host EXE")
    plan=generate_plan(sf2)
    saved=json.loads(contract.read_text(encoding="utf8"))
    for k in ("schema","private_sf2_sha256","presets","programs","scenarios"):
        require(saved.get(k)==plan[k],"capture contract mismatches actual SF2")
    report=log.read_text(encoding="utf8",errors="replace")
    require(MODE in report,"not the entire real owner-77 VST3 run; synthetic-only NOT ACCEPTED")
    require("P220_VST3_FAIL" not in report,"real VST3 reported error")
    all_lines=[l.strip() for l in report.splitlines()
               if l.strip().startswith("P220_VST3_PCM")]
    require(len(all_lines)==154,"not exactly 154 independent actual process WAV receipts")
    trials=[]
    total_callbacks=0
    seen=set()
    for case,line in zip(plan["scenarios"],all_lines):
        m=LINE.fullmatch(line)
        require(m is not None,"malformed real exported VST3 host output")
        ident,raw_prog,variant,raw_selected,raw_note,raw_velocity,raw_frames,raw_callbacks,raw_rms,raw_peak=m.groups()
        p=int(raw_prog);frames=int(raw_frames);callbacks=int(raw_callbacks)
        require(ident==case["id"] and p==case["program"]==int(raw_selected)
            and variant==case["variant"] and int(raw_note)==case["note"]
            and int(raw_velocity)==case["velocity"] and
            frames==132300 and callbacks>=130 and
            float(raw_rms)>=0.00015 and float(raw_peak)<0.99997,
            "wrong program/note/velocity, incomplete PCM, silence or clipping "+str(ident))
        require(ident not in seen,"duplicate WAV/id "+ident)
        seen.add(ident)
        path=wavdir/(ident+".wav")
        require(path.is_file() and path.stat().st_size==44+frames*4,
                "missing/truncated private stereo WAV "+ident)
        with wave.open(str(path),"rb") as w:
            require((w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes(),w.getcomptype())==
                    (2,2,44100,132300,"NONE"),
                    "wrong PCM format or duration "+ident)
        trials.append({
            "id":ident,"program":p,
            "note":case["note"],"velocity":case["velocity"],
            "controllers":case["controllers"],
            "note_off_observed":True,  # mandatory scheduled host VST3 NoteOff event
            "audio_frames":frames,"wav_sha256":sha(path),
            "vst3_program_selected":p,
            "vst3_note_on_count":1,
            "vst3_bank_selection_acknowledged":True,
            "process_callbacks":callbacks,
            "captured_from_real_exported_vst3":True,
        })
        total_callbacks+=callbacks
    require(len(trials)==154 and len(seen)==154,
            "missing original private SF2 program wav files")
    return {
        "schema":"125a-p220-real-vst3-77-capture-v1",
        "real_windows_vst3_process":True,
        "native_offline_emu8000_only":False,
        "chip":"86box_emu8000",
        "chip_scope":"EMU8000 software emulation in actual Windows VST3 (not physical AWE64)",
        "loaded_sf2_sha256":BANK_SHA,
        "module_sha256":sha(module),
        "host_exe_sha256":sha(exe),
        "process_callback_count":total_callbacks,
        "actual_original_creative_driver":"NOT RUN",
        "private_wav_data_uploaded":False,
        "physical_awe64":"NOT TESTED",
        "release_approved":False,
        "trials":trials}
def main():
    p=argparse.ArgumentParser()
    for field in ("sf2","rom","module","contract","log","wavdir","exe","out"):
        p.add_argument("--"+field,type=Path,required=True)
    a=p.parse_args()
    result=assemble(a.sf2,a.rom,a.module,a.contract,a.log,a.wavdir,a.exe)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("P220 154/154 ACTUAL independent Windows VST3 audio receipts prepared; original Creative Win95: NOT RUN here")
if __name__=="__main__":main()
