#!/usr/bin/env python3
"""Private one-off P228/P229 replay adapter for existing P48/P64/P89/P234.
No register injection, alternate VM, synthesizer, gain fitting or engine edits.
Run original P48 CLI unchanged; P64's existing baseline runs before this hook.
"""
import csv, hashlib, importlib.util, json, os, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, '/workspace/awe-v25-independent/tools')
# Only the independently corrected inventory gate is substituted; original
# P48 orchestration and driver playback remain the existing current code.
spec=importlib.util.spec_from_file_location('p83_generic_sf2','/workspace/awe-integration-report/tools/p83_generic_sf2.py')
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
import p48_86box_boot_win95 as p48
from p63_send_guest_midi import frame
from p64_original_win95_midi_trial import connect_linux_86box_fifo, send_paced_frame
from p89_compare_voice_registers import original_csv, native_trace, compare
from p234_dry_compare import decode_rows, edges, crop, stats

root=Path('/tmp/awe-sf2-117-evidence')
bank_index=int(os.environ['P229_BANK_INDEX'])
banks=['Synth 512 Bank(3).sf2','FM Dreams Sampler(1).sf2','Vintage Dreams Bank.sf2','Vintage Synth 2001.sf2']
sf2=Path('/tmp/awe-sf2-private-20261111')/banks[bank_index]
sha=hashlib.sha256(sf2.read_bytes()).hexdigest()
plan=[r for r in csv.DictReader((root/'p229-reproduced-testplan.csv').open()) if r['file']==sf2.name]
assert plan and all(r['source_sha256']==sha and r['bank']=='0' for r in plan)
native=list(csv.DictReader((root/f'p229-capture-bank-{bank_index}.csv').open()))
assert len(native)==len(plan)
selected_ids=set(int(x) for x in os.environ.get('P229_CASE_IDS','').split(',') if x)
trials=[(i,a,b) for i,(a,b) in enumerate(zip(plan,native),1) if not selected_ids or i in selected_ids]
suffix=os.environ.get('P229_REPLAY_SUFFIX','')
assert not suffix or suffix=='-fresh-layer-witness'
baseline=p48.p64_run_trial

def trace_segment(trace, start, dest):
    with trace.open('rb') as f:
        header=f.readline();f.seek(start);body=f.read()
    assert body.endswith(b'\n')
    dest.write_bytes(header+body)
    count=len(body.splitlines())
    return original_csv(dest,0,count),count

def replay(conn,out,trace,fifo,send,key,type_path,screenshot,report,**kw):
    baseline(conn,out,trace,fifo,send,key,type_path,screenshot,report,**kw)
    assert report.get('hardware')=='sbawe64_gold' and report.get('sample_ram_kib')==28672
    assert report.get('p84_universal_sf2_test') and report.get('p75_private_sample_upload_plausible')
    target=root/f'original-bank-{bank_index}{suffix}'
    target.mkdir(exist_ok=False)
    gate=Path(os.environ['EMU8K_P234_GATE']);pcm=Path(os.environ['EMU8K_P234_DRY_PCM']);stage=Path(os.environ['EMU8K_P233_STAGE'])
    assert not gate.exists() and pcm.is_file() and stage.is_file()
    fd=connect_linux_86box_fifo(fifo)
    results=[]
    try:
        for i,row,native_row in trials:
            p,n,v=map(int,(row['program'],row['note'],row['velocity']))
            assert (p,n,v)==tuple(int(native_row[k]) for k in ('program','note','velocity'))
            d=target/f'case-{i}';d.mkdir()
            # Same held note, CC7/11 and centre pan as fresh native P229;
            # original guest bank 1 is AWECP's loaded SF2 bank 0.
            controls=((120,0),(123,0),(64,0),(0,1),(7,100),(11,127),(10,64),(1,0),(91,0),(93,0))
            for cc,val in controls:send_paced_frame(fd,frame(0xb0,cc,val),conn,send)
            send_paced_frame(fd,frame(0xc0,p,0),conn,send)
            send(conn,'step 260')
            begin=trace.stat().st_size;sb=stage.stat().st_size;pb=pcm.stat().st_size
            gate.touch(exist_ok=False)
            try:
                send(conn,'step 50')
                send_paced_frame(fd,frame(0x90,n,v),conn,send)
                noteon,nrows=trace_segment(trace,begin,d/'original-noteon.csv')
                # Six actual paced UART bytes consume 150 ms BEFORE NoteOff.
                send(conn,'step 850')
                send_paced_frame(fd,frame(0x80,n,0),conn,send)
                send(conn,'step 1100')
            finally:gate.unlink(missing_ok=True)
            se=stage.stat().st_size;pe=pcm.stat().st_size
            P,Q,M=decode_rows(stage,[sb,se]);edge=edges(Q)
            hold=edge['duration_frames']
            if abs(hold-44100)>44:raise ValueError(f'actual original hold {hold} exceeds existing P234 ±44 gate')
            mm=np.memmap(pcm,mode='r',dtype='<i4').reshape(-1,2)
            on=edge['noteon_chip_frame']
            # Explicit common window: 87220 frames. Native's documented
            # 980-frame adapter publication delay is removed, no fitted shift.
            count=88200-980
            original=crop(P,mm,on,on+count,[pb,pe])
            reference=np.fromfile(root/f'private-capture-bank-{bank_index}'/f'case-{i}'/'native-preclip.i32le',dtype='<i4').reshape(-1,2)[980:]
            assert original.shape==reference.shape==(count,2)
            original.astype('<i4').tofile(d/'original-dry-window.i32le')
            onvoices=edge['noteon_layer_voices']
            last={}
            for voice,reg,val in noteon:
                if voice in onvoices:last.setdefault(voice,{})[reg]=val
            native_regs=list(csv.DictReader((root/f'private-capture-bank-{bank_index}'/f'case-{i}'/'active-voice-registers.csv').open()))
            native_seq=native_trace(root/f'private-capture-bank-{bank_index}'/f'case-{i}'/'native-port-write.trace')
            def rail(a):return int(np.count_nonzero((a < -32768)|(a > 32767)))
            result=dict(case=i,file=sf2.name,source_sha256=sha,program=p,note=n,velocity=v,
                original_driver='Win95 original Creative SBAWE.VXD in 86Box',physical_card=False,
                guest_p67='PENDING_AFTER_SHUTDOWN',original_hold_frames=hold,window_frames=count,
                native_publication_latency_removed_frames=980,
                original_chip_edges=edge,original_active_layer_count=len(onvoices),
                native_active_layer_count=len(native_regs),original_noteon_registers=last,
                native_noteon_registers=native_regs,
                original_stats=stats(original),native_stats=stats(reference),
                original_raw_overrange_values=rail(original),native_raw_overrange_values=rail(reference),
                original_dry_sha256=hashlib.sha256(original.astype('<i4').tobytes()).hexdigest(),
                native_window_sha256=hashlib.sha256(reference.astype('<i4').tobytes()).hexdigest(),
                original_trace_byte_range=[begin,trace.stat().st_size],stage_byte_range=[sb,se],dry_byte_range=[pb,pe],
                noteon_register_comparison=compare(noteon,native_seq))
            results.append(result)
            (target/'matched-results.json').write_text(json.dumps(results,indent=2)+'\n')
            print('ORIGINAL_CREATIVE_CASE',bank_index,i,len(plan),p,n,v,'layers',len(onvoices),len(native_regs),'overrange',rail(original),rail(reference),flush=True)
    finally:os.close(fd)
    report['p229_original_clipping_replay']=dict(cases=len(results),source_sha256=sha,expected_winmm_deliveries=8+len(plan)*13,physical_card='NOT RUN')

p48.p64_run_trial=replay
p48.main()
