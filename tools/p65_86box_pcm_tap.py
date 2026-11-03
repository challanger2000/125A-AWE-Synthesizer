#!/usr/bin/env python3
"""Opt-in original 86Box EMU8000 wavetable PCM -> nonblocking Linux FIFO.

Patches ONLY a throwaway clone of upstream 86Box; no nonfree OS, ROM,
driver, sample, or original 86Box source is checked into the project.
The 86Box sound mixer remains in charge of all chip/DSP processing.
"""
from __future__ import annotations
import argparse
from pathlib import Path

MARKER = "void\nwavetable_poll(UNUSED(void *priv))"
AUDIO_MARKER = "        if (sound_is_float)\n            givealbuffer_wt(outbuffer_w_ex);"

SINK = r"""
#ifndef _WIN32
/* 125A P65: Linux-only local PCM stream, AFTER original EMU8000 synthesis.
 * No blocking I/O: packet exactly 12 + 980*4 = 3932 <= PIPE_BUF 4096.
 * The sequence advances on every block including dropped/undelivered ones. */
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <signal.h>
#include <stdlib.h>
#include <stdint.h>
static void
p65_emit_original_wavetable(const int32_t *src)
{
    static int fd=-1;
    static int initialized=0;
    static const char *fifo=NULL;
    static uint32_t seq=0;
    unsigned char pkt[12 + WTBUFLEN*4];
    uint32_t count=seq++;
    int i;
    if (!initialized) {
        fifo=getenv("AWE_P65_PCM_FIFO");
        initialized=1;
        if (fifo && *fifo)
            signal(SIGPIPE,SIG_IGN); /* never crash 86Box on disconnect */
    }
    if (!fifo || !*fifo) return;
    if (fd<0) {
        fd=open(fifo,O_WRONLY|O_NONBLOCK);
        if(fd<0) return; /* host absent: keep emulation running */
    }
    pkt[0]='A';pkt[1]='W';pkt[2]='E';pkt[3]='0';
    pkt[4]=(unsigned char)count;
    pkt[5]=(unsigned char)(count>>8);
    pkt[6]=(unsigned char)(count>>16);
    pkt[7]=(unsigned char)(count>>24);
    pkt[8]=(unsigned char)WTBUFLEN;
    pkt[9]=(unsigned char)(WTBUFLEN>>8);
    pkt[10]=(unsigned char)44100;
    pkt[11]=(unsigned char)(44100>>8);
    for(i=0;i<WTBUFLEN*2;i++) {
        int32_t v=src[i];
        if(v>32767)v=32767;
        if(v< -32768)v=-32768;
        pkt[12+i*2]=(unsigned char)v;
        pkt[13+i*2]=(unsigned char)(v>>8);
    }
    /* Linux write <= PIPE_BUF to FIFO is atomic, O_NONBLOCK means
     * EAGAIN drops this entire frame rather than delaying the emulator. */
    {
        ssize_t n=write(fd,pkt,sizeof(pkt));
        if(n<0 && (errno==EPIPE||errno==EBADF)) {
            close(fd);fd=-1;
        }
    }
}
#endif
"""
CALL = """#ifndef _WIN32
        p65_emit_original_wavetable(outbuffer_w);
#endif
"""


def instrument(original: str) -> str:
    if original.count(MARKER)!=1 or original.count(AUDIO_MARKER)!=1:
        raise ValueError("Unsupported 86Box source: wavetable entry point changed")
    if "p65_emit_original_wavetable" in original:
        raise ValueError("Refuse double instrumentation")
    if "#include <86box/sound.h>" not in original:
        raise ValueError("Not the expected 86Box sound.c")
    original=original.replace(MARKER,SINK+"\n"+MARKER,1)
    original=original.replace(AUDIO_MARKER,CALL+AUDIO_MARKER,1)
    return original


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    modified=instrument(args.source.read_text(encoding="utf8"))
    args.out.write_text(modified,encoding="utf8")
    print("P65 nonblocking 44.1kHz stereo FIFO PCM bridge source instrumented")


if __name__=="__main__":
    main()
