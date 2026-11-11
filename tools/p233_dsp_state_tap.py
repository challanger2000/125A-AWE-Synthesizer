#!/usr/bin/env python3
"""P233 - non-invasive (read-only) 86Box EMU8000 DSP state and component taps.

Instrument disposable source copies only. Native and upstream have different
emu8k_update implementations; inject identical stage observation into each.
Never change signal processing, driver, voice registers, or original ROM.
Output is numerical CSV and INIT/HWCF snapshots, no sample data.
"""
from __future__ import annotations
import argparse
from pathlib import Path

COMMON=r'''
/* P233: measurement-only chip stage observer. No writes into chip audio.
 * M rows: frame,n,stage,raw L²/R²/Mid²/Side²/LR,rails; component reverb
 * and chorus computed as difference of successive signal stages.
 * S rows: exact INIT1..4/HWCF4-5 and FX delay/LFO/reverb state.
 * 44.1k clock; absolute frame counter is observer-only, not emulation state.
 */
static FILE *p233_fp;
static int p233_attempted;
static unsigned long long p233_frame;
static unsigned long long p233_last_snapshot;
static FILE *p233_open(void) {
    if(!p233_attempted) {
        const char *p=getenv("EMU8K_P233_STAGE");
        p233_attempted=1;
        if(p && *p) {
            p233_fp=fopen(p,"w");
            if(p233_fp) {
                fprintf(p233_fp,"P233,version=1,rate=44100,stage=post_voice_reverb_chorus_final\n");
                fflush(p233_fp);
            }
        }
    }
    return p233_fp;
}
static void p233_m(FILE *f, const char *stage, const int32_t *src,
                   const int32_t *subtract, int frames)
{
    long double ll=0,rr=0,mm=0,ss=0,lr=0;
    unsigned long long rails=0;
    for (int i=0;i<frames;i++) {
        const long double l=(long double)src[2*i]-(subtract?(long double)subtract[2*i]:0);
        const long double r=(long double)src[2*i+1]-(subtract?(long double)subtract[2*i+1]:0);
        ll+=l*l; rr+=r*r; mm+=((l+r)/2)*((l+r)/2);
        ss+=((l-r)/2)*((l-r)/2); lr+=l*r;
        if(!subtract && (l>32767 || l< -32768 || r>32767 || r< -32768)) rails++;
    }
    fprintf(f,"M,%llu,%d,%s,%.0Lf,%.0Lf,%.0Lf,%.0Lf,%.0Lf,%llu\n",
        p233_frame,frames,stage,ll,rr,mm,ss,lr,rails);
}
static void p233_state(FILE *f, emu8k_t *e) {
    fprintf(f,"S,%llu,HWCF4,%08X\n",p233_frame,(unsigned)e->hwcf4);
    fprintf(f,"S,%llu,HWCF5,%08X\n",p233_frame,(unsigned)e->hwcf5);
    fprintf(f,"S,%llu,HWCF3,%04X\n",p233_frame,(unsigned)e->hwcf3);
    for(int a=0;a<4;a++) {
        const uint16_t *v=a==0?e->init1:a==1?e->init2:a==2?e->init3:e->init4;
        fprintf(f,"S,%llu,INIT%d",p233_frame,a+1);
        for(int i=0;i<32;i++)fprintf(f,",%04X",(unsigned)v[i]);
        fprintf(f,"\n");
    }
    fprintf(f,"S,%llu,FX,reverb_out=%d,reverb_link=%d,reverb_type=%d,"
        "reverb_reflect=%u,rv_delay_l=%d,rv_delay_r=%d,rv_tail_pos=%d,"
        "chorus_write=%d,chorus_feedback=%d,chorus_delay=%d,chorus_lfo=%llu,"
        "chorus_depth=%.9g,chorus_offset=%.9g\n",p233_frame,
        (int)e->reverb_engine.out_mix,(int)e->reverb_engine.link_return_amp,
        (int)e->reverb_engine.link_return_type,(unsigned)e->reverb_engine.refl_in_amp,
        e->reverb_engine.tailL.bufsize,e->reverb_engine.tailR.bufsize,
        e->reverb_engine.tailL.read_pos,
        e->chorus_engine.write,e->chorus_engine.feedback,
        e->chorus_engine.delay_samples_central,
        (unsigned long long)e->chorus_engine.lfo_pos.addr,
        e->chorus_engine.lfodepth_multip,
        e->chorus_engine.delay_offset_samples_right);
    /* Active voice sends, layer pan and envelope state, for attribution. */
    for(int i=0;i<32;i++){
        emu8k_voice_t *v=&e->voice[i];
        if(!v->env_engine_on && !v->cvcf_curr_volume)continue;
        fprintf(f,"V,%llu,%d,ptrx=%08X,csl=%08X,pan_l=%d,pan_r=%d,"
            "reverb_send=%u,chorus_send=%u,atkhldv=%04X,vstate=%d,volume=%u\n",
            p233_frame,i,(unsigned)v->ptrx,(unsigned)v->csl,
            v->vol_l,v->vol_r,(unsigned)v->ptrx_revb_send,(unsigned)v->csl_chor_send,
            (unsigned)v->atkhldv,v->vol_envelope.state,
            (unsigned)v->cvcf_curr_volume);
    }
}
static void p233_emit(emu8k_t *e,int count,
       const int32_t *dry,const int32_t *rev,
       const int32_t *chor,const int32_t *out)
{
    FILE *f=p233_open();
    if(!f || count<=0)return;
    p233_m(f,"dry",dry,NULL,count);
    p233_m(f,"reverb",rev,dry,count);
    p233_m(f,"chorus",chor,rev,count);
    p233_m(f,"output",out,NULL,count);
    p233_frame+=(unsigned long long)count;
    if(p233_frame/4410 != p233_last_snapshot) {
        p233_state(f,e);
        p233_last_snapshot=p233_frame/4410;
    }
    fflush(f);
}
'''

def assert_unique(source: str, token: str, note: str) -> None:
    if source.count(token)!=1:
        raise ValueError(f"{note}: expected unique marker {token[:130]!r}; got {source.count(token)}")

def patch(source: str, kind: str) -> str:
    if "P233: measurement-only" in source:
        raise ValueError("P233 already instrumented")
    assert kind in ("original","native")
    marker=("static void /* AWE32Emu: one chunk; emu8k_update() below splits at state dump frames */\nemu8k_update_chunk(emu8k_t *emu8k)\n{"
            if kind=="native" else "void\nemu8k_update(emu8k_t *emu8k)\n{")
    assert_unique(source,marker,kind)
    source=source.replace(marker,COMMON+"\n"+marker,1)
    # Only allocate temporary on-stack taps on runs with P233 explicitly enabled.
    variables="""
    int32_t p233_before[WTBUFLEN*2],p233_after_rev[WTBUFLEN*2],
            p233_after_chor[WTBUFLEN*2];
    int p233_enabled=p233_open()!=NULL;
"""
    source=source.replace(marker,marker+variables,1)
    if kind=="original":
        beginning="    /* Only run reverb/chorus/EQ when at least one voice was active. */"
        reverb="        emu8k_work_reverb(&emu8k->reverb_in_buffer[emu8k->pos], buf, &emu8k->reverb_engine, num_samples);"
        chorus="        emu8k_work_chorus(&emu8k->chorus_in_buffer[emu8k->pos], buf, &emu8k->chorus_engine, num_samples);"
        end="    /* Update EMU clock. */\n    emu8k->wc += num_samples;"
        assert_unique(source,beginning,kind)
        source=source.replace(beginning,beginning+
           "\n    if(p233_enabled)memcpy(p233_before,&emu8k->buffer[emu8k->pos*2],num_samples*2*sizeof(int32_t));"
           "\n    if(p233_enabled)memcpy(p233_after_rev,p233_before,num_samples*2*sizeof(int32_t));"
           "\n    if(p233_enabled)memcpy(p233_after_chor,p233_before,num_samples*2*sizeof(int32_t));",1)
        assert_unique(source,reverb,kind)
        source=source.replace(reverb,reverb+
            "\n        if(p233_enabled)memcpy(p233_after_rev,buf,num_samples*2*sizeof(int32_t));",1)
        assert_unique(source,chorus,kind)
        source=source.replace(chorus,chorus+
            "\n        if(p233_enabled)memcpy(p233_after_chor,buf,num_samples*2*sizeof(int32_t));",1)
    else:
        beginning="    /* AWE32Emu: the effects always run, like on the chip."
        reverb="        emu8k_work_reverb(&emu8k->reverb_in_buffer[emu8k->pos], buf, &emu8k->reverb_engine, num_samples, emu8k->mute_reverb_return);"
        chorus="        emu8k_work_chorus(&emu8k->chorus_in_buffer[emu8k->pos], buf, &emu8k->chorus_engine, num_samples, emu8k->mute_chorus_return);"
        end="    /* Update EMU clock. */\n    emu8k->wc += num_samples;"
        assert_unique(source,beginning,kind)
        source=source.replace(beginning,
          "    if(p233_enabled)memcpy(p233_before,&emu8k->buffer[emu8k->pos*2],num_samples*2*sizeof(int32_t));"
          "\n    if(p233_enabled)memcpy(p233_after_rev,p233_before,num_samples*2*sizeof(int32_t));"
          "\n    if(p233_enabled)memcpy(p233_after_chor,p233_before,num_samples*2*sizeof(int32_t));\n"
          +beginning,1)
        # The production fork compiles REVERB_FITTED by default. A probe
        # placed after the legacy (inactive) emu8k_work_reverb call would
        # wrongly attribute the entire fitted reverb return to chorus.
        # Capture after #endif, which observes whichever reverb is active.
        assert_unique(source,reverb,kind)
        assert_unique(source,chorus,kind)
        post_reverb="#endif\n"+chorus
        assert_unique(source,post_reverb,kind)
        source=source.replace(post_reverb,
             "#endif\n        if(p233_enabled)memcpy(p233_after_rev,buf,num_samples*2*sizeof(int32_t));\n"+chorus,1)
        source=source.replace(chorus,chorus+
          "\n        if(p233_enabled)memcpy(p233_after_chor,buf,num_samples*2*sizeof(int32_t));",1)
    assert_unique(source,end,kind)
    source=source.replace(end,
        "    if(p233_enabled)p233_emit(emu8k,num_samples,p233_before,p233_after_rev,"
        "p233_after_chor,&emu8k->buffer[emu8k->pos*2]);\n"+end,1)
    return source

def selftest():
    for kind,minimum in (("original",1),("native",1)):
        # A wrong/incomplete patch must refuse to inject.
        try:patch("void\nemu8k_update(emu8k_t *emu8k)\n{}",kind)
        except ValueError:pass
        else:raise AssertionError("incomplete source accepted: "+kind)
    print("P233_PATCH_SOURCE_GUARDS_PASS")

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--source",type=Path)
    a.add_argument("--out",type=Path)
    a.add_argument("--kind",choices=["original","native"])
    a.add_argument("--self-test",action="store_true")
    args=a.parse_args()
    if args.self_test:return selftest()
    if not args.source or not args.out or not args.kind:a.error("source,out,kind required")
    if args.source.resolve()==args.out.resolve():a.error("never edit source in place")
    result=patch(args.source.read_text(),args.kind)
    args.out.write_text(result)
    print("P233_PRIVATE_DSP_INSTRUMENTED",args.kind,
          "stage=dry,reverb_difference,chorus_difference,output; INIT/HWCF/FX state")
if __name__=="__main__":main()
