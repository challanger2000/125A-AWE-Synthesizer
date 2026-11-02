#!/usr/bin/env python3
"""Host-side private 86Box wavetable PCM receiver. No DSP or SF2 interpreter.

Reads fixed 3932-byte FIFO frames; exports only numeric signal statistics.
This is a prototype live audio transport, NOT a finished VST3 processor.
"""
from __future__ import annotations
import array
import math
import os
from pathlib import Path
import select
import struct
import threading
import time

HEADER = struct.Struct("<4sIHH")
FRAME_COUNT = 980
PACKET_BYTES=HEADER.size+FRAME_COUNT*4

class PcmStats:
    def __init__(self):
        self.packets=0
        self.frames=0
        self.sequence_gaps=0
        self.nonzero_frames=0
        self.peak=0
        self.energy=0
        self.previous=None

    def accept(self,data: bytes):
        if len(data)!=PACKET_BYTES:
            raise ValueError("Invalid audio payload length")
        magic, seq, frames, rate=HEADER.unpack_from(data)
        if magic!=b"AWE0" or frames!=FRAME_COUNT or rate!=44100:
            raise ValueError("Invalid 86Box PCM format")
        if self.previous is not None:
            self.sequence_gaps+=(seq-self.previous-1)&0xFFFFFFFF
        self.previous=seq
        pcm=array.array("h")
        pcm.frombytes(data[HEADER.size:])
        if struct.pack("=H",1)!=b"\x01\0":pcm.byteswap()
        if len(pcm)!=frames*2:raise ValueError("Wrong channel count")
        for val in pcm:
            x=abs(val)
            if x>self.peak:self.peak=x
            self.energy+=val*val
        self.nonzero_frames+=sum(pcm[2*i]!=0 or pcm[2*i+1]!=0 for i in range(frames))
        self.frames+=frames
        self.packets+=1

    def report(self):
        n=self.frames*2
        return {
            "packets":self.packets,
            "frames":self.frames,
            "sequence_gaps":self.sequence_gaps,
            "nonzero_frames":self.nonzero_frames,
            "peak_dbfs":round(20*math.log10(max(self.peak/32768.0,1e-15)),2),
            "rms_dbfs":round(20*math.log10(max(math.sqrt(self.energy/n)/32768.0,1e-15)),2) if n else -300,
            "sample_rate":44100,
            "channels":2,
            "actual_emu8000_pcm_observed":bool(self.nonzero_frames),
            "raw_audio_uploaded":False
        }


class PcmReceiver:
    def __init__(self, path: Path):
        self.path=path
        self.stats=PcmStats()
        self._error=None
        self._stop=threading.Event()
        self._thread=None

    def start(self):
        if self.path.exists():raise FileExistsError(self.path)
        os.mkfifo(self.path,0o600)
        self._thread=threading.Thread(target=self._run,daemon=True)
        self._thread.start()

    def _run(self):
        buf=bytearray()
        try:
            fd=os.open(self.path,os.O_RDONLY|os.O_NONBLOCK)
            try:
                while not self._stop.is_set():
                    readable,_,_=select.select([fd],[],[],.05)
                    if not readable:continue
                    block=os.read(fd,65536)
                    if not block:continue
                    buf.extend(block)
                    while len(buf)>=PACKET_BYTES:
                        packet=bytes(buf[:PACKET_BYTES])
                        del buf[:PACKET_BYTES]
                        self.stats.accept(packet)
            finally:
                os.close(fd)
        except Exception as e:
            self._error=str(e)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(2)
            if self._thread.is_alive():
                raise RuntimeError("PCM receiver did not stop")
        if self._error:raise RuntimeError("PCM receiver error: "+self._error)
        self.path.unlink(missing_ok=True)
        return self.stats.report()
