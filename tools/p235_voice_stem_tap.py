#!/usr/bin/env python3
"""P235 P234 read-only physical EMU8000 voices 0 and 3 postfilter/pan preFX.

Patches ONLY ephemeral C sources already instrumented with P233 + P234.
Per voice original 86Box uses the real *buf++ address, not the ideal sample
position: this also detects the known stock 86Box silent-sample advance rule.
Recorded interleaved little-endian int32 stereo samples remain RUNNER PRIVATE.
"""
import argparse
from pathlib import Path

HELPER=r'''
/* P235 runner-private, observational physical voice component taps. */
static FILE *p235_v0_file, *p235_v3_file;
static int p235_started;
static void p235_emit(const int32_t *voice0,const int32_t *voice3,int count) {
    if (!p234_is_active() || count<=0) return;
    if (!p235_started) {
        const char *v0=getenv("EMU8K_P235_VOICE_0_PCM");
        const char *v3=getenv("EMU8K_P235_VOICE_3_PCM");
        if(!v0||!v3||!*v0||!*v3)abort();
        p235_v0_file=fopen(v0,"wb");
        p235_v3_file=fopen(v3,"wb");
        if(!p235_v0_file||!p235_v3_file)abort();
        p235_started=1;
    }
    size_t n=(size_t)count*2;
    if(fwrite(voice0,sizeof(int32_t),n,p235_v0_file)!=n)abort();
    if(fwrite(voice3,sizeof(int32_t),n,p235_v3_file)!=n)abort();
    fflush(p235_v0_file);fflush(p235_v3_file);
}
'''
def one(s,old,new):
    if s.count(old)!=1: raise ValueError(f"P235 UNIQUE MARKER FAIL count={s.count(old)}: {old[:90]}")
    return s.replace(old,new,1)
def patch(s,kind):
    if kind not in ("native","original"): raise ValueError("bad kind")
    if "P235 runner-private" in s: raise ValueError("already instrumented")
    if "P234: read-only original/native dry voice PCM" not in s: raise ValueError("missing P234")
    if kind=="original":
        marker="void\nemu8k_update(emu8k_t *emu8k)\n{"
        mixing='                    (*buf++) += (dat * emu_voice->vol_l) >> 8;\n                    (*buf++) += (dat * emu_voice->vol_r) >> 8;'
        patchmix='''                    /* The stock 86Box pointer itself determines the actual
                     * placement of each physical voice component. */
                    if(p235_v0 && c==0) {
                        size_t idx=(size_t)(buf-&emu8k->buffer[emu8k->pos*2]);
                        if(idx+1 >= (size_t)num_samples*2)abort();
                        p235_v0[idx]+=(dat * emu_voice->vol_l)>>8;
                        p235_v0[idx+1]+=(dat * emu_voice->vol_r)>>8;
                    }
                    if(p235_v3 && c==3) {
                        size_t idx=(size_t)(buf-&emu8k->buffer[emu8k->pos*2]);
                        if(idx+1 >= (size_t)num_samples*2)abort();
                        p235_v3[idx]+=(dat * emu_voice->vol_l)>>8;
                        p235_v3[idx+1]+=(dat * emu_voice->vol_r)>>8;
                    }
'''+mixing
    else:
        marker="static void /* AWE32Emu: one chunk; emu8k_update() below splits at state dump frames */\nemu8k_update_chunk(emu8k_t *emu8k)\n{"
        mixing='                    emu8k->buffer[pos * 2] += (dat * emu_voice->vol_l) >> 8;\n                    emu8k->buffer[pos * 2 + 1] += (dat * emu_voice->vol_r) >> 8;'
        patchmix='''                    if(p235_v0 && c==0) {
                        size_t idx=(size_t)(pos-emu8k->pos)*2;
                        if(idx+1 >= (size_t)num_samples*2)abort();
                        p235_v0[idx]+=(dat * emu_voice->vol_l)>>8;
                        p235_v0[idx+1]+=(dat * emu_voice->vol_r)>>8;
                    }
                    if(p235_v3 && c==3) {
                        size_t idx=(size_t)(pos-emu8k->pos)*2;
                        if(idx+1 >= (size_t)num_samples*2)abort();
                        p235_v3[idx]+=(dat * emu_voice->vol_l)>>8;
                        p235_v3[idx+1]+=(dat * emu_voice->vol_r)>>8;
                    }
'''+mixing
    # Helpers precede actual update routine, after P234 function is defined.
    s=one(s,marker,HELPER+"\n"+marker)
    s=one(s,"    int            num_active = 0;",
      '''    int            num_active = 0;
    int32_t *p235_v0=NULL,*p235_v3=NULL;
    if(p234_is_active()) {
        p235_v0=(int32_t *)calloc((size_t)num_samples*2,sizeof(int32_t));
        p235_v3=(int32_t *)calloc((size_t)num_samples*2,sizeof(int32_t));
        if(!p235_v0||!p235_v3)abort();
    }''')
    s=one(s,mixing,patchmix)
    # The reverb branch starts after voices have fully mixed and before
    # the p233/p234 common observation emits the complete dry voice signal.
    anchor=("    /* Only run reverb/chorus/EQ when at least one voice was active. */"
            if kind=="original" else
            "    /* AWE32Emu: the effects always run, like on the chip.")
    s=one(s,anchor,
      '''    if(p235_v0) {
        p235_emit(p235_v0,p235_v3,num_samples);
        free(p235_v0);free(p235_v3);
    }
'''+anchor)
    return s

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--kind",choices=["native","original"])
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:
        for k in ("native","original"):
            try:patch("",k)
            except ValueError:pass
            else:raise AssertionError("P235 accepted empty source")
        print("P235_STEM_INSTRUMENTATION_GUARDS_PASS")
        return
    if not a.source or not a.out or not a.kind:p.error("source/out/kind required")
    if a.source.resolve()==a.out.resolve():p.error("source cannot be overwritten")
    a.out.write_text(patch(a.source.read_text(),a.kind))
    print("P235_ISOLATED_PHYSICAL_VOICES_0_3",a.kind)

if __name__=="__main__": main()
