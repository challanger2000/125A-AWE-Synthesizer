#!/usr/bin/env python3
"""P234 original/native pre-FX sample-accurate dry PCM + MIDI edge observer.

Inject ONLY into disposable, already P233-instrumented 86Box C source.
NEVER patch an installed VST3 or commit a modified production DSP C file.
Per-voice DCYSUSV/DCYSUS and pointer writes are recorded at chip frames,
not inferred from milliseconds. Raw int32 audio is always runner-private.
"""
from __future__ import annotations

import argparse
from pathlib import Path

OBSERVER=r'''
/* P234: read-only original/native dry voice PCM, gate-controlled on runner.
 * P rows map chip frames to byte offsets in the *private* signed int32le PCM.
 * Q rows identify actual register WRITE edges at current DSP clock frame.
 * File gate is created/removed around existing P48 Win95 audio capture.
 * Never change register values or the chip's output buffers.
 */
#include <unistd.h>
static FILE *p234_dry_fp;
static int p234_dry_tried;
static const char *p234_gate;
static unsigned long long p234_dry_bytes;
static int p234_is_active(void) {
    if (!p234_dry_tried) {
        const char *path=getenv("EMU8K_P234_DRY_PCM");
        p234_gate=getenv("EMU8K_P234_GATE");
        p234_dry_tried=1;
        if(path && *path && p234_gate && *p234_gate)
            p234_dry_fp=fopen(path,"wb");
    }
    return p234_dry_fp && p234_gate && access(p234_gate,F_OK)==0;
}
static void p234_dry_write(unsigned long long frame,
                          const int32_t *dry,int n,FILE *f) {
    if(!p234_is_active())return;
    const size_t bytes=(size_t)n*2*sizeof(int32_t);
    if(fwrite(dry,1,bytes,p234_dry_fp)!=bytes)abort();
    fflush(p234_dry_fp);
    fprintf(f,"P,%llu,%d,%llu\n",frame,n,p234_dry_bytes);
    p234_dry_bytes+=(unsigned long long)bytes;
    fflush(f);
}
static void p234_register_edge(emu8k_t *e,uint16_t addr,uint16_t val){
    if (!p234_is_active() || addr!=0xA20 || e->cur_voice>=32)
        return;
    const int r=e->cur_reg;
    if(r!=5 && r!=7)return;
    FILE *f=p233_open();
    if(!f)abort();
    /* Q frame,physical_voice,register_number(5 DCYSUSV/7 DCYSUS),value */
    fprintf(f,"Q,%llu,%d,%d,%04X\n",p233_frame,(int)e->cur_voice,r,(unsigned)val);
    fflush(f);
}
'''

def patch(source: str) -> str:
    if "P234: read-only original/native dry voice PCM" in source:
        raise ValueError("source already has P234 taps")
    marker="static FILE *p233_fp;"
    if source.count(marker)!=1 or "static void p233_emit" not in source:
        raise ValueError("input must contain complete P233 DSP-stage instrumentation")
    source=source.replace(marker,OBSERVER+"\n"+marker,1)
    # We need p233_open/p233_frame already declared for P234 observer.
    # Put P234 definitions *after* p233_emit, before emu8k_update in original,
    # or before emu8k_update_chunk in native; forward declarations not needed.
    source=source.replace(OBSERVER+"\n"+marker,marker,1)
    end="static void p233_emit(emu8k_t *e,int count,"
    idx=source.index(end)
    endmarker="    fflush(f);\n}\n"
    endidx=source.find(endmarker,idx)
    if endidx<0:raise ValueError("P233 emit terminator missing")
    insert=endidx+len(endmarker)
    source=source[:insert]+"\n"+OBSERVER+"\n"+source[insert:]
    called="    if(!f || count<=0)return;"
    if source.count(called)!=1:raise ValueError("P233 emit call guard not unique")
    source=source.replace(called,called+
        "\n    p234_dry_write(p233_frame,dry,count,f);",1)
    # The earlier emu8k_outw body updates audio before applying register writes.
    # Clock stamp therefore refers to the exact register-write boundary.
    marker="void\nemu8k_outw(uint16_t addr, uint16_t val, void *priv)\n{"
    if source.count(marker)!=1:raise ValueError("original/native port-write marker mismatch")
    beginning=source.index(marker)
    sub=source[beginning:]
    update="    emu8k_update(emu8k);"
    if update not in sub[:1500]:raise ValueError("unverified emu8k_outw timing")
    sub=sub.replace(update,update+"\n    p234_register_edge(emu8k,addr,val);",1)
    source=source[:beginning]+sub
    return source

def self_test():
    for bad in ("", "void\nemu8k_outw(uint16_t addr, uint16_t val, void *priv)\n{}"):
        try:patch(bad)
        except ValueError:pass
        else:raise AssertionError("P234 accepted invalid input")
    print("P234_DRY_CAPTURE_SOURCE_GUARDS_PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",type=Path)
    ap.add_argument("--out",type=Path)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:return self_test()
    if not args.source or not args.out:ap.error("--source and --out needed")
    if args.source.resolve()==args.out.resolve():ap.error("never edit source in place")
    args.out.write_text(patch(args.source.read_text()))
    print("P234_DRY_PCM_AND_TRUE_REGISTER_EDGE_CAPTURE_INSTRUMENTED")
if __name__=="__main__":
    main()
