"""Independent SF2 stimuli + amplitude/spectral/loop oracles; no private media.

The executable supplies int16 stereo PCM from the real 86Box chip. Decisions
use signal windows, harmonic projection and absolute timing, never a stored
copy of the implementation's parameter mapping. No assert (Release safe).
"""
import argparse
import array
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile


def u16(*values):
    return struct.pack('<'+'H'*len(values), *(v & 65535 for v in values))


def u32(*values):
    return struct.pack('<'+'I'*len(values), *values)


def name(value):
    return value.encode('ascii')[:20].ljust(20, b'\0')


def chunk(tag, data):
    return tag.encode('ascii')+u32(len(data))+data+(b'\0' if len(data) & 1 else b'')


def sf2(path, generators, end=None, loop_start=256, loop_end=None, guard_at=None,words=4096):
    # Three harmonics provide separately measurable low/mid/high references.
    pcm=[round(6000*math.sin(2*math.pi*n/256)
               +2500*math.sin(2*math.pi*5*n/256)
               +1500*math.sin(2*math.pi*17*n/256)) for n in range(words)]
    if end is None:end=words
    if loop_end is None:loop_end=words-256
    if guard_at is not None:
        pcm[guard_at:guard_at+46]=[0]*46
    info=chunk('ifil',u16(2,1))+chunk('INAM',b'125A independent audio oracle\0')
    phdr=name('Audio oracle')+u16(0,0,0)+u32(0,0,0)
    phdr+=name('EOP')+u16(0,0,1)+u32(0,0,0)
    gens=list(generators)+[(53,0)]
    shdr=name('Harmonics')+u32(0,end,loop_start,loop_end,44100)+bytes([60,0])+u16(0,1)
    shdr+=name('EOS')+bytes(26)
    pdta=b''.join(chunk(k,v) for k,v in [
        ('phdr',phdr),('pbag',u16(0,0,1,0)),('pmod',bytes(10)),('pgen',u16(41,0)),
        ('inst',name('Harmonics')+u16(0)+name('EOI')+u16(1)),
        ('ibag',u16(0,0,len(gens),0)),('imod',bytes(10)),
        ('igen',b''.join(u16(k,v) for k,v in gens)),('shdr',shdr)])
    data=b'sfbk'+chunk('LIST',b'INFO'+info)
    data+=chunk('LIST',b'sdta'+chunk('smpl',u16(*(pcm+[0]*46))))
    data+=chunk('LIST',b'pdta'+pdta)
    path.write_bytes(chunk('RIFF',data))


DRY=[(33,-12000),(34,-12000),(35,-12000),(36,-12000),(37,0),(38,-3600),
     (25,-12000),(26,-2400),(27,-12000),(28,-1200),(29,1000),(30,-2400),
     (54,1),(8,13500)]
PAD=[(33,-1200),(34,-1200),(35,-1200),(36,0),(37,0),(38,0),
     (54,1),(8,13500)]


def rms(pcm,rate,start,end):
    values=pcm[int(rate*start)*2:int(rate*end)*2]
    return math.sqrt(sum(v*v for v in values)/max(1,len(values)))/32768


def harmonic(pcm,rate,start,end,multiple):
    values=pcm[int(rate*start)*2:int(rate*end)*2:2]
    w=2*math.pi*(44100/256)*multiple/rate
    a=sum(v*math.cos(w*i) for i,v in enumerate(values))
    b=sum(v*math.sin(w*i) for i,v in enumerate(values))
    return math.hypot(a,b)/max(1,len(values))/32768


def main():
    ap=argparse.ArgumentParser();ap.add_argument('renderer');ap.add_argument('output')
    args=ap.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    rows=[];checks=[]
    def check(value,label):
        checks.append({'pass':bool(value),'label':label})
        print(('PASS ' if value else 'FAIL ')+label,flush=True)
    with tempfile.TemporaryDirectory(prefix='125a-p170-') as directory:
        root=Path(directory);rom=root/'zero.rom';rom.write_bytes(bytes(1048576))
        def render(label,gens=DRY,controls=None,rate=44100,block=128,off=2.5,pedal=None,cc91=0,cc93=0,**sample):
            font=root/'oracle.sf2';sf2(font,gens,**sample);target=root/'pcm.bin'
            result=subprocess.run([args.renderer,str(rom),str(font),str(target),str(rate),
                str(block),str(off),*[str(v) for v in (controls or [0]*12)],
                *([] if pedal is None else [str(pedal)])],
                capture_output=True,text=True,timeout=45,
                env=dict(os.environ,P170_ORACLE_CC91=str(cc91),P170_ORACLE_CC93=str(cc93)))
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)
            regs=json.loads(result.stdout.strip().splitlines()[-1]);pcm=array.array('h',target.read_bytes())
            if sys.byteorder!='little':pcm.byteswap()
            rows.append(dict(label=label,rate=rate,block=block,controls=controls or [0]*12,
                sf2_generators=gens,sample_overrides=sample,note_off_s=off,pedal_release_s=pedal,
                midi_cc91=cc91,midi_cc93=cc93,sf2_sha256=hashlib.sha256(font.read_bytes()).hexdigest(),
                pcm_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                registers=regs,rms_early=rms(pcm,rate,.03,.08),rms_late=rms(pcm,rate,1.5,2),
                peak=max(map(abs,pcm))/32768))
            # Synthetic data only; retain every actual sample for falsification.
            (out/(label+'.s16le')).write_bytes(target.read_bytes())
            return pcm,regs
        for rate,block in [(44100,128),(48000,256),(96000,511)]:
            neutral,_=render(f'pad-neutral-{rate}',PAD,rate=rate,block=block)
            click,regs=render(f'pad-click-{rate}',PAD,[1,1,1,1]+[0]*8,rate=rate,block=block)
            peak=max(map(abs,click));last=max((i//2 for i,v in enumerate(click) if abs(v)>max(2,peak*.001)),default=rate*3)
            # Existing FIFO latency is ~22ms; allow <50ms sound after it.
            check(peak>50 and last/rate<.075 and rms(click,rate,.1,2)<1e-4,
                  f'held pad becomes audible <=50ms click before NoteOff ({rate} Hz), last={last/rate:.6f}s')
            check(rms(neutral,rate,1.5,2)>.001,f'neutral pad remains sustained ({rate} Hz)')
        # No arbitrary 0->1% replacement: the existing onset must change smoothly.
        onset=[]
        for value in [0,.01,.05,.2,.5,.75,1]:
            ctl=[value,0,0,0]+[0]*8
            pcm,reg=render(f'attack-{value}',PAD,ctl)
            peak=max(map(abs,pcm));on=next((i//2/44100 for i,v in enumerate(pcm) if abs(v)>max(4,peak*.1)),3)
            onset.append(on)
        check(all(b<=a+.002 for a,b in zip(onset,onset[1:])),f'AMP shortening monotone: {onset}')
        check(abs(onset[1]-onset[0])<.05,'AMP 0->1% has no absolute-rate jump')
        for control,title in [(1,'decay'),(2,'sustain'),(3,'release')]:
            measurements=[]
            for value in [0,.01,.05,.2,.5,.75,1]:
                ctl=[0]*12
                if control==1:ctl[0]=ctl[2]=1
                ctl[control]=value
                gens=PAD if control==1 else [p for p in DRY if p[0]!=38]+[(38,1200)]
                pcm,_=render(f'{title}-{value}',gens,ctl,off=.5 if control==3 else 2.5)
                lo,hi=(.55,.8) if control==3 else ((.1,.5) if control==1 else (1.,1.5))
                measurements.append(rms(pcm,44100,lo,hi))
            check(measurements[0]>measurements[-1]*5 and all(b<=a*1.03+1e-5 for a,b in zip(measurements,measurements[1:])),
                  f'AMP {title} audio sweep {measurements}')
        release_zero=[]
        for value in [0,.01,.05,1]:
            pcm,_=render(f'release-zero-rate-{value}',
                [p for p in DRY if p[0]!=38]+[(38,8000)],[0,0,0,value]+[0]*8,off=.5)
            release_zero.append(rms(pcm,44100,.55,.8))
        check(all(b<=a*1.03+1e-5 for a,b in zip(release_zero,release_zero[1:])),
              'AMP release zero-rate fallback remains monotone '+str(release_zero))
        # This SF2 has NO filter route: require spectral modulation, not changed registers alone.
        dry,_=render('filter-neutral')
        filtered,_=render('filter-adsr',controls=[0]*4+[1,.5,1,1]+[0]*4)
        def colour(pcm,start,end):
            return harmonic(pcm,44100,start,end,17)/max(1e-8,harmonic(pcm,44100,start,end,1))
        early=colour(filtered,.035,.1);late=colour(filtered,1.5,2)
        check(harmonic(filtered,44100,.035,.1,1)>1e-4 and early>late*4,
              f'FILTER ADSR actually closes spectrum with absent SF2 route: early={early:.6g} late={late:.6g}')
        check(colour(dry,1.5,2)>late*4,'neutral filter route preserves bright original')
        # P174 INDEPENDENT DARK-PATCH FALSIFICATION. A newly synthesized
        # positive PEFE route cannot have a modulation peak BRIGHTER than the
        # original patch if the stated contract is "peak at original cutoff".
        # With a low initial SF2 filter generator the original depth=96
        # clipped IFATN at register zero, then the 86Box chip raised highs
        # 17x or more. Keep this actual PCM/spectral oracle in Release tests.
        for dark_fc in [4000,6000,8000]:
            dark_gens=[p for p in DRY if p[0]!=8]+[(8,dark_fc)]
            dark_original,_=render(f'p174-dark-fc{dark_fc}-original',dark_gens)
            dark_edited,dark_regs=render(f'p174-dark-fc{dark_fc}-filter',dark_gens,
                [0]*4+[1,.5,1,1]+[0]*4)
            base_high=harmonic(dark_original,44100,.035,.1,17)
            edited_high=harmonic(dark_edited,44100,.035,.1,17)
            check(edited_high<=base_high*1.10+1e-6,
                  f'P174 no unintended high-frequency brightening above original low-cutoff patch: '
                  f'fc={dark_fc}, base={base_high:.8g}, overlay={edited_high:.8g}, '
                  f'PEFE={dark_regs["pefe"]&255}')
            if dark_fc==6000:
                dark_late=harmonic(dark_edited,44100,1.5,2,17)
                check((dark_regs['pefe']&255)>0 and dark_late<edited_high*.7,
                      f'P174 useful short filter-envelope sweep remains at dark cutoff: '
                      f'peak={edited_high:.8g}, late={dark_late:.8g}')
        # Existing signed filter depths remain patch-owned; both must still
        # respond to the envelope timing, without inversion/removal of route.
        for route in [-4800,4800]:
            gens=[p for p in DRY if p[0]!=8]+[(8,10000),(11,route)]
            original,original_regs=render(f'filter-route-{route}',gens)
            edited,edited_regs=render(f'filter-route-{route}-edited',gens,[0]*4+[1,1,1,1]+[0]*4)
            check(original_regs['pefe']==edited_regs['pefe'] and original!=edited,
                  f'existing signed filter route retained and envelope audible ({route})')
        for index,title in enumerate(['attack','decay','sustain','release']):
            values=[]
            for value in [0,.01,.05,.2,.5,.75,1]:
                gens=[p for p in DRY if p[0] not in (29,38)]+[(29,1000 if index==1 else 0),(38,2400)]
                if index==0:
                    gens=[p for p in gens if p[0]!=26]+[(26,1200)] # two-second original filter attack
                # Another, inaudible-at-this-stage control keeps route depth
                # constant while the tested ADSR stage is swept in isolation.
                filt=[0,0,0,1] if index==0 else [1,0,0,0]
                filt[index]=value
                pcm,_=render(f'filter-{title}-{value}',gens,[0]*4+filt+[0]*4,off=.5 if index==3 else 2.5)
                window=[(.03,.1),(.1,.4),(1.,1.5),(.6,.8)][index]
                values.append(colour(pcm,*window))
            increasing=index==0
            ordered=all((b+.003>=a*.9) if increasing else (b<=a*1.1+.003)
                        for a,b in zip(values,values[1:]))
            dynamic=values[-1]>values[0]*1.5 if increasing else values[0]>values[-1]*1.5
            check(ordered and dynamic,f'FILTER {title} spectral sweep {values}')
        colours=[]
        for value in [0,.01,.05,.2,.5,.75,1]:
            pcm,_=render(f'cutoff-{value}',controls=[0]*8+[value,0,0,0])
            colours.append(colour(pcm,.3,.5))
        check(colours[0]>colours[-1]*8 and all(b<=a*1.2+.003 for a,b in zip(colours,colours[1:])),
              f'cutoff reduction spectral sweep {colours}')
        resonance=[]
        for value in [0,.2,.5,.75,1]:
            pcm,_=render(f'resonance-{value}',controls=[0]*8+[.5,value,0,0])
            resonance.append(harmonic(pcm,44100,.3,.5,5)/max(1e-9,harmonic(pcm,44100,.3,.5,1)))
        check(resonance[-1]>resonance[0]*1.5,'resonance boosts near-cutoff harmonic relative to fundamental '+str(resonance))
        # A nonzero patch setting must not make the whole upper control
        # range a clipped dead zone. Compare actual PCM, not knob readback.
        for index,generator,title,mid in [(8,(8,9000),'cutoff',.75),(9,(9,100),'resonance',.5),
                                          (10,(16,500),'reverb',.5),(11,(15,500),'chorus',.5)]:
            gens=[p for p in DRY if p[0]!=generator[0]]+[generator]
            render(f'headroom-{title}-original',gens)
            a=[0]*12;b=[0]*12;a[index]=mid;b[index]=1
            middle,_=render(f'headroom-{title}-middle',gens,a)
            maximum,_=render(f'headroom-{title}-max',gens,b)
            check(middle!=maximum,f'{title} retains audible headroom above {mid*100:g}% on a nonneutral patch')
        for index,op,title,controls in [(10,16,'reverb',{'cc91':127}),(11,15,'chorus',{'cc93':127})]:
            gens=[p for p in DRY if p[0]!=op]+[(op,500)]
            _,initial_regs=render(f'headroom-midi-{title}-original',gens,**controls)
            actual_send=((initial_regs['ptrx']>>8)&255) if index==10 else ((initial_regs['csl']>>24)&255)
            check(actual_send==(242 if index==10 else 241),
                  title+' fixture confirms actual patch plus channel MIDI send before audio comparison')
            a=[0]*12;b=[0]*12;a[index]=.5;b[index]=1
            middle,_=render(f'headroom-midi-{title}-middle',gens,a,**controls)
            maximum,_=render(f'headroom-midi-{title}-max',gens,b,**controls)
            check(middle!=maximum,f'{title} retains audible headroom with MIDI send already present')
        fx={}
        for index,title in [(10,'reverb'),(11,'chorus')]:
            for amount in [0,.2,.5,1]:
                ctl=[0]*12;ctl[index]=amount
                pcm,reg=render(f'{title}-send-{amount}',controls=ctl,off=.25)
                fx[title,amount]=pcm
            if title=='reverb':
                tail=[rms(fx[title,a],44100,.6,1.2) for a in [0,.2,.5,1]]
                check(tail[-1]>tail[0]+1e-4 and all(b>=a*.95 for a,b in zip(tail,tail[1:])),
                      'reverb send increases measured wet tail '+str(tail))
            else:
                check(fx[title,0]!=fx[title,1],'chorus send changes actual stereo PCM')
                lo,hi=int(.05*44100)*2,int(.2*44100)*2
                original=fx[title,0][lo:hi]
                wet=[math.sqrt(sum((x-y)**2 for x,y in zip(original,fx[title,a][lo:hi]))/(hi-lo))/32768
                     for a in [0,.2,.5,1]]
                check(wet[1]>1e-4 and all(b>=a*.95 for a,b in zip(wet,wet[1:]))
                      and .4<wet[2]/max(wet[3],1e-9)<.6,
                      'chorus measured wet residual grows with send '+str(wet))
            # A send preserves the dry attack. It never promises 100% wet.
            check(rms(fx[title,1],44100,.03,.04)>.001,title+' maximum send retains dry output')
        looped={}
        for mode in [0,1,3]:
            gens=[p for p in DRY if p[0] not in (38,54)]+[(38,0),(54,mode)]
            pcm,regs=render(f'loop-{mode}',gens,off=1.,loop_end=4080)
            looped[mode]=(pcm,regs)
        check(rms(looped[0][0],44100,.3,.8)<1e-4 and rms(looped[1][0],44100,.3,.8)>.001,
              'one-shot finishes; continuous loop holds before NoteOff')
        # Opening the loop lets the remaining sample play out. Allow its
        # full 4096-word duration plus existing FIFO latency after NoteOff.
        check(rms(looped[1][0],44100,1.15,1.25)>.0001 and rms(looped[3][0],44100,1.15,1.25)<1e-4,
              'mode3 exits short-tail loop at NoteOff; mode1 retains loop during release')
        held,_=render('loop-3-sustain',[p for p in DRY if p[0] not in (38,54)]+[(38,0),(54,3)],
                      off=1.,pedal=1.5,loop_end=4080)
        check(rms(held,44100,1.1,1.2)>.001 and rms(held,44100,1.65,1.75)<1e-4,
              'mode3 exits only after sustain-pedal release, not at held NoteOff')
        # End offset must truncate a one-shot independently of the header end.
        short,_=render('one-shot-end-offset',[p for p in DRY if p[0]!=54]+[(54,0),(1,-3072)],guard_at=1024)
        check(rms(short,44100,.07,.12)<1e-4,'SF2 endAddrsOffset truncates actual one-shot PCM')
        coarse,_=render('one-shot-coarse-end',[p for p in DRY if p[0]!=54]+[(54,0),(12,-1)],
                        words=36864,guard_at=4096)
        check(rms(coarse,44100,.15,.3)<1e-4,'SF2 endAddrsCoarseOffset truncates actual one-shot PCM')
    (out/'measurements.json').write_text(json.dumps({'rows':rows,'checks':checks},indent=2))
    return 0 if all(c['pass'] for c in checks) else 1


if __name__=='__main__':
    sys.exit(main())
