"""Independent raw-QPC/ETW analysis. Running time is NOT pure DSP time.
All callback rows, including underfilled transitions and every deadline miss,
remain in the artifact. Matched-load statistics are a separate population.
"""
from pathlib import Path
import bisect,collections,csv,json,math,sys

def read(path):
    if not path.exists():return []
    with path.open(newline='') as f:return list(csv.DictReader(f))
def percentile(values,p):
    v=sorted(values)
    return v[max(0,math.ceil(len(v)*p)-1)] if v else None

def analyze(folder):
    folder=Path(folder);rows=read(folder/'callbacks.csv');assert rows,'no callback evidence'
    meta_path=folder/'etw/trace-meta.json';meta=json.loads(meta_path.read_text()) if meta_path.exists() else {}
    switches=sorted(read(folder/'etw/cswitch.csv'),key=lambda r:int(r['qpc']))
    running=collections.defaultdict(list);off=collections.defaultdict(list);entered={};left={}
    for e in switches:
        t=int(e['qpc']);old=int(e['old_tid']);new=int(e['new_tid'])
        if old in entered:
            start=entered.pop(old)
            if t>=start:running[old].append((start,t))
        left[old]=(t,int(e['old_state']),int(e['old_wait_reason']))
        if new in left:
            start,state,reason=left.pop(new)
            if t>=start:off[new].append((start,t,state,reason))
        entered[new]=t
    starts={tid:[x[0] for x in intervals] for tid,intervals in running.items()}
    def overlap(r):
        tid=int(r['tid']);a=int(r['qpc_begin']);b=int(r['qpc_end']);h=int(r['qpc_hz'])
        seq=running.get(tid,[]);i=max(0,bisect.bisect_right(starts.get(tid,[]),a)-1);on=0
        while i<len(seq) and seq[i][0]<b:
            lo,hi=seq[i];on+=max(0,min(hi,b)-max(lo,a));i+=1
        return on*1e6/h
    calibration={r['phase']:r for r in rows if r['phase'].startswith('calibration_')}
    clock_ok=meta.get('perf_frequency')==int(rows[0]['qpc_hz'])
    sleep=calibration.get('calibration_sleep');busy=calibration.get('calibration_busy')
    sleep_off=float(sleep['wall_us'])-overlap(sleep) if sleep else None
    busy_on=overlap(busy) if busy else None
    valid=bool(meta and meta.get('process_trace_result')==0 and meta.get('events_lost')==0 and meta.get('buffers_lost')==0 and clock_ok and sleep_off is not None and sleep_off>5000 and busy_on is not None and busy_on>1000)
    heap=read(folder/'etw/heap.csv');heap.sort(key=lambda r:int(r['qpc']));heap_times=[int(r['qpc']) for r in heap]
    def heap_in(r):
        a=int(r['qpc_begin']);b=int(r['qpc_end']);tid=r['tid'];return [e for e in heap[bisect.bisect_left(heap_times,a):bisect.bisect_right(heap_times,b)] if e['tid']==tid]
    positive=heap_in(calibration['calibration_heap']) if 'calibration_heap' in calibration else []
    positive_sizes=sorted({int(e['size']) for e in positive if e['size_valid']=='1'})
    heap_complete=bool(meta and meta.get('process_trace_result')==0 and meta.get('events_lost')==0 and meta.get('buffers_lost')==0 and clock_ok and all(s in positive_sizes for s in [37,73,91,131]))
    memory_events=[]
    for r in rows:
        if r['phase']=='memory':
            for e in heap_in(r):memory_events.append(dict(e,case=r['case'],callback=r['index']))
    groups=collections.defaultdict(list);misses=[]
    for r in rows:
        if r['phase']!='measure':continue
        key=(int(r['frames']),int(r['voices']),int(r['mode']));groups[key].append(r)
        if float(r['wall_us'])>float(r['budget_us']):
            attribution='NOT_RUN_ETW_COVERAGE';on=overlap(r) if valid else None
            ready=waiting=0.0
            if valid:
                a,b=int(r['qpc_begin']),int(r['qpc_end']);h=int(r['qpc_hz'])
                for lo,hi,state,reason in off.get(int(r['tid']),[]):
                    if hi<a:continue
                    if lo>b:break
                    duration=max(0,min(hi,b)-max(lo,a))*1e6/h
                    if state==1:ready+=duration
                    if state==5:waiting+=duration
                excess=float(r['wall_us'])-float(r['budget_us'])
                if ready>excess and on<float(r['budget_us']):attribution='PREEMPTION_SUFFICIENT'
                elif waiting>excess and on<float(r['budget_us']):attribution='WAITING_SUFFICIENT_NEEDS_STACK'
                elif ready+waiting>excess and on<float(r['budget_us']):attribution='MIXED_OFF_CPU_SUFFICIENT'
                elif on>=float(r['budget_us']):attribution='SCHEDULED_RUNTIME_OVER_BUDGET_NOT_PURE_DSP_PROOF'
                else:attribution='OFF_CPU_SUFFICIENT_REASON_UNKNOWN'
            misses.append(dict(r,scheduled_us=on,ready_off_cpu_us=ready,waiting_us=waiting,attribution=attribution))
    summary=[]
    for (frames,n,mode),data in sorted(groups.items()):
        matched=[r for r in data if r['matched']=='1']
        def values(part):
            w=[float(r['wall_us']) for r in part]
            return dict(n=len(w),median_us=percentile(w,.5),p99_us=percentile(w,.99),max_us=max(w) if w else None,overruns=sum(float(r['wall_us'])>float(r['budget_us']) for r in part))
        summary.append(dict(frames=frames,voices=n,mode=mode,all=values(data),matched=values(matched),underfilled=sum(int(r['allocated_before'])<n or int(r['allocated_after'])<n or int(r['nonzero_before'])<n or int(r['nonzero_after'])<n for r in data),generation_transitions=sum(r['generation_before']!=r['generation_after'] for r in data)))
    samples=read(folder/'etw/samples.csv');samples.sort(key=lambda r:int(r['qpc']));sample_times=[int(r['qpc']) for r in samples];top=collections.Counter()
    # ETL emits time-ordered events. Only CPU samples falling IN process count.
    for r in rows:
        if r['phase']!='measure':continue
        a,b=int(r['qpc_begin']),int(r['qpc_end'])
        for e in samples[bisect.bisect_left(sample_times,a):bisect.bisect_right(sample_times,b)]:
            if e['tid']==r['tid']:top[e['symbol'] or 'UNRESOLVED']+=1
    result=dict(rows=len(rows),measured=sum(x['all']['n'] for x in summary),cases=summary,etw=meta,etw_context_valid=valid,calibration_sleep_off_us=sleep_off,calibration_busy_on_us=busy_on,clock_ok=clock_ok,heap_positive_sizes=positive_sizes,heap_backend_positive_control_complete=heap_complete,memory_phase_heap_events=len(memory_events),memory_phase_events=memory_events[:100],attributions=dict(collections.Counter(r['attribution'] for r in misses)),worst=sorted(misses,key=lambda r:float(r['wall_us']),reverse=True)[:30],top_sampled_symbols=top.most_common(30),target_asio_tested=False,realtime_verdict='NOT RUN')
    (folder/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    if misses:
        with (folder/'deadline-events.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(misses[0]));w.writeheader();w.writerows(misses)
    print(json.dumps({k:result[k] for k in ['measured','etw_context_valid','calibration_sleep_off_us','calibration_busy_on_us','heap_positive_sizes','heap_backend_positive_control_complete','memory_phase_heap_events','attributions','realtime_verdict']}))
    return result
if __name__=='__main__':analyze(sys.argv[1])
