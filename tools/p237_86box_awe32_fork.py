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
    args=p.parse_args()
    if args.command=="install": result=install(args.out)
    elif args.command=="capture": result=capture(args.binary,args.vm,args.out,args.roms,args.duration_seconds,args.disposable_vm_copy)
    else:result=audit_trace_and_wav(args.trace,args.wav)
    print(json.dumps(result,indent=2))


if __name__=="__main__":main()
