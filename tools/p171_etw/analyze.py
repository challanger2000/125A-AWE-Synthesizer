"""Audit only: intersect raw QPC callbacks with decoded Windows CSwitch events.

Scheduled time includes interrupts, measurement overhead and any executing
code; it is never labelled pure DSP time. Heap attribution is not performed.
"""
import argparse
import base64
import bisect
import collections
import csv
import hashlib
import json
from pathlib import Path
import zlib


def read(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))


class Intervals:
    def __init__(self,events):
        self.running=collections.defaultdict(list);self.off=collections.defaultdict(list)
        entered={};left={}
        for e in sorted(events,key=lambda r:int(r['qpc'])):
            t=int(e['qpc']);old=int(e['old_tid']);new=int(e['new_tid'])
            if old in entered:
                start=entered.pop(old)
                if t>=start:self.running[old].append((start,t))
            left[old]=(t,int(e['old_state']),int(e['old_wait_reason']))
            if new in left:
                start,state,reason=left.pop(new)
                if t>=start:self.off[new].append((start,t,state,reason))
            entered[new]=t
        self.starts={k:[x[0] for x in v] for k,v in self.running.items()}
        self.off_starts={k:[x[0] for x in v] for k,v in self.off.items()}

    def measure(self,row,meta):
        tid=int(row['tid']);a=int(row['qpc_start']);b=int(row['qpc_end']);hz=int(row['qpc_frequency'])
        if hz<=0 or b<a:raise RuntimeError('invalid QPC callback')
        on=off=ready=waiting=0
        for seq,starts,is_off in ((self.running.get(tid,[]),self.starts.get(tid,[]),False),
                                  (self.off.get(tid,[]),self.off_starts.get(tid,[]),True)):
            i=max(0,bisect.bisect_right(starts,a)-1)
            while i<len(seq) and seq[i][0]<b:
                lo,hi=seq[i][:2];ticks=max(0,min(hi,b)-max(lo,a))
                if is_off:
                    off+=ticks
                    if seq[i][2]==1:ready+=ticks
                    if seq[i][2]==5:waiting+=ticks
                else:on+=ticks
                i+=1
        valid=(meta.get('process_trace_result')==0 and meta.get('events_lost')==0
               and meta.get('buffers_lost')==0 and meta.get('perf_frequency')==hz
               and meta.get('target_cswitch',0)>0 and abs(on+off-(b-a))<=2)
        return {'qpc_window_us':(b-a)*1e6/hz,'scheduled_us':on*1e6/hz,
                'off_cpu_us':off*1e6/hz,'ready_us':ready*1e6/hz,
                'waiting_us':waiting*1e6/hz,'coverage_complete':valid}


def classify(row,m,control_ok):
    if not control_ok or not m['coverage_complete']:return 'NOT_RUN_ETW_COVERAGE_OR_CONTROL'
    budget=float(row['deadline_us']);excess=m['qpc_window_us']-budget
    # Require a margin for the timestamps surrounding the original wall timer.
    if m['scheduled_us']>=budget:return 'SCHEDULED_RUNTIME_OVER_BUDGET_NOT_PURE_DSP_PROOF'
    if m['ready_us']>excess+5:return 'READY_PREEMPTION_SUFFICIENT'
    if m['waiting_us']>excess+5:return 'WAITING_SUFFICIENT_NEEDS_STACK'
    return 'MIXED_OR_UNKNOWN_OFF_CPU_SUFFICIENT'


def publish(marker,data):
    digest=hashlib.sha256(data).hexdigest()
    encoded=base64.b64encode(zlib.compress(data,9)).decode()
    parts=[encoded[i:i+48000] for i in range(0,len(encoded),48000)]
    for i,part in enumerate(parts):
        print(f'::notice title=P171 ETW evidence::{marker}_{i+1}_OF_{len(parts)}_SHA_{digest}:{part}')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['control','audit'])
    ap.add_argument('csv');ap.add_argument('decoded');ap.add_argument('output')
    ap.add_argument('--control');ap.add_argument('--expected-csv-sha');ap.add_argument('--product-sha');ap.add_argument('--run-id');args=ap.parse_args()
    source=Path(args.csv);out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if args.expected_csv_sha and digest!=args.expected_csv_sha:raise RuntimeError('wrong original callback CSV')
    decoded=Path(args.decoded);meta=json.loads((decoded/'trace-meta.json').read_text())
    rows=read(source);intervals=Intervals(read(decoded/'cswitch.csv'))
    measured=[dict(r,**intervals.measure(r,meta)) for r in rows]
    if args.mode=='control':
        ok=(len(measured)==4 and all(r['coverage_complete'] for r in measured)
            and sum(r['phase']=='sleep' and r['off_cpu_us']>10000 for r in measured)==2
            and sum(r['phase']=='busy' and r['scheduled_us']>5000 for r in measured)==2)
        result={'control_passed':ok,'trace_meta':meta,'rows':measured,
                'scope':'separate decoder calibration on this Windows runner, not retroactive heap coverage'}
    else:
        control=json.loads(Path(args.control).read_text());ok=control.get('control_passed') is True
        late=[dict(r,attribution=classify(r,r,ok)) for r in measured if r['late']=='1']
        result={'product_source_sha':args.product_sha,
                'original_run_id':args.run_id,'raw_csv_sha256':digest,'trace_meta':meta,
                'decoder_control_passed':ok,'callbacks':len(rows),
                'callbacks_with_complete_context':sum(r['coverage_complete'] for r in measured),
                'deadline_misses':late,'heap_attribution':'NOT RUN',
                'pure_dsp_attribution':'NOT ESTABLISHED BY CSWITCH',
                'physical_asio':'NOT RUN','commercial_release':'NO-GO'}
        if len(rows)!=14400:raise RuntimeError('incomplete original callback population')
        with (out/'callbacks-with-context.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(measured[0]));writer.writeheader();writer.writerows(measured)
    data=(json.dumps(result,indent=2)+'\n').encode();(out/'result.json').write_bytes(data)
    publish('P171_ETW_RESULT',data)
    print('P171_ETW_STATUS',args.mode,'control',ok,'callbacks',len(rows),
          'complete',sum(r['coverage_complete'] for r in measured),'misses',len(result.get('deadline_misses',[])))
    if not ok:raise SystemExit(1)


if __name__=='__main__':main()
