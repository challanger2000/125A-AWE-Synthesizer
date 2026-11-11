#!/usr/bin/env python3
"""Pinned 86Box-AWE32 fork installer and private EMU8000 register/WAV recorder.

This is a sidecar, NOT a replacement for the upstream 86Box+P45 automation
backend. A fork trace proves emulated register activity, not physical fidelity.
The launcher only operates on an explicitly approved disposable VM copy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import tempfile
import urllib.request
import wave
import zipfile

TAG = "v6.0-AWE32-0.93"
RELEASE = f"https://github.com/turican0/86Box-AWE32/releases/download/{TAG}/86Box-AWE32-{TAG}-Windows-x64.zip"
ZIP_SHA256 = "cefd28b691bfe1149719d26f54729356af91f9c3f713cfa6bab747aa0fa16b09"
SOURCE_COMMIT = "fee1e8197782"  # tag tree version recorded September 30, 2026


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def install_archive(archive: Path, dest: Path, expected: str = ZIP_SHA256) -> dict:
    if not dest.is_dir():
        raise ValueError("Destination must already exist (never overwrite an existing VM)")
    if any(dest.iterdir()):
        raise ValueError("Destination must be empty; refusing to overwrite files")
    actual = sha256(archive)
    if actual.lower() != expected.lower():
        raise ValueError(f"Pinned fork release SHA-256 mismatch: {actual}")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if not members or sum(i.file_size for i in members) > 600_000_000:
            raise ValueError("Unexpected or oversized 86Box archive")
        for item in members:
            p = PurePosixPath(item.filename.replace("\\", "/"))
            if p.is_absolute() or ".." in p.parts or not p.parts or ":" in p.parts[0]:
                raise ValueError("Unsafe path in 86Box release ZIP")
            # ZIP symlinks are not supported; prevent crossing the destination.
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Symlink in fork ZIP is not supported")
        z.extractall(dest)
    binaries = sorted(p for p in dest.rglob("86Box.exe") if p.is_file())
    if len(binaries) != 1:
        raise ValueError(f"Expected one 86Box.exe, got {len(binaries)}")
    report = {"backend":"turican0/86Box-AWE32", "tag":TAG,
              "upstream_source_commit_prefix":SOURCE_COMMIT,
              "release_sha256":actual,"exe_relative":str(binaries[0].relative_to(dest)),
              "exe_sha256":sha256(binaries[0]),"run_vm":False,
              "hardware_audio_fidelity":"NOT_TESTED"}
    (dest/"P237-fork-install.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report


def install(dest: Path) -> dict:
    if dest.exists() and any(dest.iterdir()):
        raise ValueError("Install directory not empty")
    with tempfile.TemporaryDirectory(prefix="p237-download-") as folder:
        zip_path=Path(folder)/"fork.zip"
        with urllib.request.urlopen(RELEASE,timeout=150) as src, zip_path.open("wb") as dst:
            shutil.copyfileobj(src,dst,1024*1024)
        dest.mkdir(parents=True,exist_ok=True)
        return install_archive(zip_path,dest)


def audit_trace_and_wav(trace: Path, audio: Path) -> dict:
    if not trace.is_file() or trace.stat().st_size == 0:
        raise ValueError("EMU8K_TRACE missing or empty")
    writes=reads=0
    last=-1
    for line in trace.read_text(encoding="utf-8",errors="strict").splitlines():
        line=line.strip()
        if not line or line.startswith("#"):
            continue
        parts=line.split()
        if parts[0]=="R":
            reads+=1;parts=parts[1:]
        else:
            writes+=1
        if len(parts)!=3:
            raise ValueError("Malformed EMU8K_TRACE row")
        frame=int(parts[0]);int(parts[1],16);int(parts[2],16)
        if frame<last:
            raise ValueError("Nonmonotonic EMU8000 clock in trace")
        last=frame
    if not writes:
        raise ValueError("No real guest EMU8000 port writes recorded")
    with wave.open(str(audio),"rb") as w:
        if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(2,2,44100):
            raise ValueError("Fork WAV must be stereo PCM16 at 44.1 kHz")
        frames=w.getnframes()
        if frames<4410:
            raise ValueError("Fork produced less than 100ms chip audio")
        nonzero=rail=0
        while True:
            raw=w.readframes(16384)
            if not raw:break
            for (v,) in struct.iter_unpack("<h",raw):
                nonzero+=(v!=0)
                rail+=(v==32767 or v==-32768)
    return {"EMU8K_TRACE_writes":writes,"EMU8K_TRACE_reads":reads,
            "chip_wav_frames":frames,"chip_nonzero_samples":nonzero,
            "chip_pcm16_rail_samples":rail,
            "original_Creative_driver_activity_verified":False,
            "physical_hardware_audio_fidelity":"NOT_TESTED"}


def capture(binary:Path,vm:Path,out:Path,roms:Path|None,duration:int,ack:bool)->dict:
    if not ack:
        raise ValueError("Explicit --disposable-vm-copy confirmation is mandatory")
    if os.name!="nt":
        raise ValueError("The published P237 capture backend targets Windows x64 only")
    binary=binary.resolve();vm=vm.resolve();out=out.resolve()
    if not binary.is_file() or binary.name.lower()!="86box.exe":
        raise ValueError("Expected real fork 86Box.exe")
    if not (vm/"86box.cfg").is_file():
        raise ValueError("Missing existing VM configuration: 86box.cfg")
    if duration<1 or duration>1200:
        raise ValueError("Capture duration must be between 1 and 1200 seconds")
    if out.exists():
        raise ValueError("Private capture output already exists; refusing overwrite")
    if vm==out or vm in out.parents or out in vm.parents:
        raise ValueError("VM directory and capture output must be separate")
    if roms and not roms.is_dir():
        raise ValueError("ROM directory not found")
    out.mkdir(parents=True)
    trace=out/"EMU8K-original-Creative.trace"
    wav=out/"EMU8000-digital.wav"
    env=os.environ.copy()
    env.update({"EMU8K_TRACE":str(trace),"AWE32_WAV":str(wav)})
    command=[str(binary),"-P",str(vm)]
    if roms:command.extend(["-R",str(roms.resolve())])
    with (out/"86Box-host.log").open("wb") as log:
        proc=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,cwd=str(vm))
        try:
            proc.wait(timeout=duration)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:proc.wait(timeout=12)
            except subprocess.TimeoutExpired:
                proc.kill();proc.wait(timeout=10)
    report=audit_trace_and_wav(trace,wav)
    report.update({"backend":"turican0/86Box-AWE32","tag":TAG,
                   "binary_sha256":sha256(binary),
                   "trace_sha256":sha256(trace),"wav_sha256":sha256(wav),
                   "capture_duration_limit_seconds":duration,
                   "vm_is_disposable_copy_user_attested":True})
    (out/"P237-fork-capture.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report



def _p237_voice_tools():
    # Reuse the already hardware-tested P89 register naming and voice-slot
    # normalization. Do not maintain a second inconsistent EMU8000 map.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "p237_p89", Path(__file__).with_name("p89_compare_voice_registers.py"))
    if spec is None or spec.loader is None:
        raise RuntimeError("P89 original-driver register decoder unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def note_registers(path: Path, first: int, last: int) -> list[tuple[int, str, int]]:
    """Use actual fork/125A 44.1kHz port writes, not guessed driver metadata."""
    if first < 0 or last <= first:
        raise ValueError("Invalid true EMU8000 note window")
    p89 = _p237_voice_tools()
    pointer = None
    previous_frame = -1
    result = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            words = line.split()
            if words[0] == "R":
                words = words[1:]
                read = True
            else:
                read = False
            if len(words) != 3:
                raise ValueError("Malformed authentic fork/native trace row")
            frame = int(words[0])
            port = int(words[1], 16)
            value = int(words[2], 16)
            if frame < previous_frame:
                raise ValueError("Nonmonotonic chip trace frame")
            previous_frame = frame
            if read:
                continue
            if port == 0xE22:
                pointer = value
            elif first <= frame < last and port in p89.PORTS:
                if pointer is None:
                    raise ValueError("EMU8000 note data before register pointer")
                item = p89.normalized(port, value, pointer)
                if item is not None:
                    result.append(item)
    if len(result) < 3 or not any(
        reg in ("PSST_LO", "CSL_LO", "CCCA_LO", "ATKHLDV",
                "DCYSUSV", "IFATN", "VTFT_HI") for _, reg, _ in result):
        raise ValueError("No verified note/voice register activity; possible driver-init-only trace")
    return result


def _read_pcm_window(path: Path, first: int, frames: int):
    import array
    import sys
    if first < 0 or not 4410 <= frames <= 220500:
        raise ValueError("Select a genuine 100ms–5s digital 44.1kHz note window")
    with wave.open(str(path), "rb") as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate(),
            w.getcomptype()) != (2, 2, 44100, "NONE"):
            raise ValueError("Fork and native PCM must both be 44.1kHz stereo PCM16")
        if first + frames > w.getnframes():
            raise ValueError("Requested note window exceeds recorded chip PCM")
        w.setpos(first)
        raw = w.readframes(frames)
    if len(raw) != 4 * frames:
        raise ValueError("Incomplete original digital chip audio")
    values = array.array("h")
    values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    if not any(values):
        raise ValueError("Silent fork/native note window")
    return values, raw


def _pcm_comparison(fork, native):
    import math
    if len(fork) != len(native) or len(fork) < 8820:
        raise ValueError("Unequal or too-short PCM note windows")
    n = len(fork)
    fp = sum(int(x)*int(x) for x in fork)
    np = sum(int(y)*int(y) for y in native)
    delta = sum((int(x)-int(y))**2 for x,y in zip(fork,native))
    max_delta = max(abs(int(x)-int(y)) for x,y in zip(fork,native))
    hop = 882  # 441 stereo frames = 10ms
    bands = n//hop
    e_f = [math.sqrt(sum(int(x)*int(x) for x in fork[k*hop:(k+1)*hop])/hop)
           for k in range(bands)]
    e_n = [math.sqrt(sum(int(x)*int(x) for x in native[k*hop:(k+1)*hop])/hop)
           for k in range(bands)]
    af = sum(e_f)/bands
    an = sum(e_n)/bands
    cross = sum((x-af)*(y-an) for x,y in zip(e_f,e_n))
    norm = math.sqrt(sum((x-af)**2 for x in e_f)*sum((y-an)**2 for y in e_n))
    correlation = round(cross/norm,5) if norm > 1e-12 else None
    return {
        "pcm_samples_compared":n,
        "sample_exact_equal":all(x==y for x,y in zip(fork,native)),
        "fork_rms_dbfs":round(10*math.log10(max(fp/n,1e-20)/(32768**2)),4),
        "native_rms_dbfs":round(10*math.log10(max(np/n,1e-20)/(32768**2)),4),
        "native_minus_fork_rms_db":round(10*math.log10(max(np,1e-20)/max(fp,1e-20)),4),
        "difference_rms_dbfs":round(10*math.log10(max(delta/n,1e-20)/(32768**2)),4),
        "max_sample_delta_int16":max_delta,
        "envelope_10ms_correlation":correlation,
        "no_gain_normalization":True,
        "physical_card_parity_proven":False,
    }


def compare_real_fork_with_125a(
    fork_trace: Path, native_trace: Path, fork_wav: Path, native_wav: Path,
    fork_capture: Path, guest_report: Path, match_manifest: Path,
) -> dict:
    """Evidence-only: original Creative in the calibrated fork vs 125A DSP."""
    manifest = json.loads(match_manifest.read_text(encoding="utf-8"))
    guest = json.loads(guest_report.read_text(encoding="utf-8"))
    captured = json.loads(fork_capture.read_text(encoding="utf-8"))
    for flag in ("agent_launched_in_actual_win95",
                 "original_creative_winmm_endpoint_selected", "audio_observed"):
        if guest.get(flag) is not True:
            raise ValueError("Unverified original Creative Win95 guest: "+flag)
    if (captured.get("backend") != "turican0/86Box-AWE32"
            or captured.get("tag") != TAG
            or captured.get("vm_is_disposable_copy_user_attested") is not True
            or captured.get("trace_sha256") != sha256(fork_trace)
            or captured.get("wav_sha256") != sha256(fork_wav)):
        raise ValueError("Actual pinned P237 fork capture identity or SHA256 mismatch")
    required = ("rom_sha256","sf2_sha256","midi","effects","chip_settings")
    fork_config = manifest.get("fork")
    native_config = manifest.get("native")
    if not isinstance(fork_config,dict) or not isinstance(native_config,dict):
        raise ValueError("Both independently captured audio states are required")
    if any(k not in fork_config or k not in native_config for k in required):
        raise ValueError("Missing matched ROM/SF2/MIDI/effects/chip state evidence")
    for k in required:
        if fork_config[k] != native_config[k]:
            raise ValueError("Input state differs between fork and native: "+k)
    for k in ("rom_sha256","sf2_sha256"):
        v = fork_config[k]
        if not isinstance(v,str) or (v!="ROM_ONLY" and
           (len(v)!=64 or any(c not in "0123456789abcdef" for c in v))):
            raise ValueError("Invalid original ROM/SF2 fingerprint")
    midi = fork_config["midi"]
    if not isinstance(midi,dict) or any(k not in midi for k in
            ("bank","program","note","velocity","channel","hold_frames")):
        raise ValueError("MIDI bank/program/note/velocity/channel/hold required")
    if not all(isinstance(midi[k],int) for k in midi) or not (
            0<=midi["program"]<128 and 0<=midi["note"]<128
            and 1<=midi["velocity"]<=127 and 0<=midi["channel"]<16
            and midi["hold_frames"]>0):
        raise ValueError("Invalid original Creative MIDI event")
    fw, nw = manifest.get("fork_window"), manifest.get("native_window")
    if not isinstance(fw,dict) or not isinstance(nw,dict):
        raise ValueError("Missing original note register/audio window boundaries")
    for w in (fw,nw):
        if not all(isinstance(w.get(k),int) for k in ("start_frame","frames")):
            raise ValueError("No sample-clock-anchored note window")
        if w["start_frame"]<0 or not 4410<=w["frames"]<=220500:
            raise ValueError("Invalid sample-clock-anchored note duration")
    if fw["frames"] != nw["frames"]:
        raise ValueError("Original and native comparison durations differ")
    p89 = _p237_voice_tools()
    a = note_registers(fork_trace,fw["start_frame"],fw["start_frame"]+fw["frames"])
    b = note_registers(native_trace,nw["start_frame"],nw["start_frame"]+nw["frames"])
    registers = p89.compare(a,b)
    orig_pcm, orig_raw = _read_pcm_window(fork_wav,fw["start_frame"],fw["frames"])
    ours_pcm, ours_raw = _read_pcm_window(native_wav,nw["start_frame"],nw["frames"])
    audio = _pcm_comparison(orig_pcm,ours_pcm)
    if registers["register_series_different"]:
        classification = "ORIGINAL_CREATIVE_TO_125A_REGISTER_OR_STATE_TRANSLATION_DIFFERS"
    elif not audio["sample_exact_equal"]:
        classification = "EQUAL_NOTE_REGISTERS_BUT_DIGITAL_PCM_DIFFERS_CHECK_FULL_CHIP_RAM_FX_AND_DSP"
    else:
        classification = "SAMPLE_EXACT_FOR_THIS_MATCHED_NOTE_WINDOW_ONLY"
    return {
        "reference":"turican0/86Box-AWE32 original Creative Win95 driver",
        "fork_release_tag":TAG,
        "source":"REAL_CAPTURE_REQUIRED; NO_SYNTHETIC_PARITY_CLAIM",
        "fork_capture_manifest_sha256":sha256(fork_capture),
        "guest_original_creative_win95_proven":True,
        "identical_ROM_SF2_MIDI_effects_chip_settings":True,
        "midi":midi,
        "registers":registers,
        "digital_pcm":audio,
        "fork_pcm_window_sha256":hashlib.sha256(orig_raw).hexdigest(),
        "native_pcm_window_sha256":hashlib.sha256(ours_raw).hexdigest(),
        "finding":classification,
        "additional_real_AWE32_AWE64_hardware_validation_required":True,
        "release_fidelity_verified":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sp=p.add_subparsers(dest="command",required=True)
    i=sp.add_parser("install",help="Fetch and SHA-256 verify pinned Windows fork, without running VM")
    i.add_argument("--out",type=Path,required=True)
    c=sp.add_parser("capture",help="Run installed fork on explicitly disposable Windows VM")
    c.add_argument("--binary",required=True,type=Path)
    c.add_argument("--vm",required=True,type=Path)
    c.add_argument("--out",required=True,type=Path)
    c.add_argument("--roms",type=Path)
    c.add_argument("--duration-seconds",type=int,default=60)
    c.add_argument("--disposable-vm-copy",action="store_true")
    a=sp.add_parser("audit",help="Validate already-recorded fork trace/WAV without launching 86Box")
    a.add_argument("--trace",required=True,type=Path)
    a.add_argument("--wav",required=True,type=Path)
    ab=sp.add_parser("compare",help="Actual pinned-fork Creative-note vs native 125A registers and digital PCM")
    for opt in ("fork-trace","native-trace","fork-wav","native-wav",
                "fork-capture","guest-report","match-manifest","out"):
        ab.add_argument("--"+opt,required=True,type=Path)
    args=p.parse_args()
    if args.command=="install": result=install(args.out)
    elif args.command=="capture": result=capture(args.binary,args.vm,args.out,args.roms,args.duration_seconds,args.disposable_vm_copy)
    elif args.command=="audit": result=audit_trace_and_wav(args.trace,args.wav)
    else:
        result=compare_real_fork_with_125a(
            args.fork_trace,args.native_trace,args.fork_wav,args.native_wav,
            args.fork_capture,args.guest_report,args.match_manifest)
        if args.out.exists():
            raise ValueError("Refusing to overwrite original P237 comparison result")
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
