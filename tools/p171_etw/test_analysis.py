"""Analytic time lines challenge preemption, waiting and invalid traces."""
from analyze import Intervals,classify

row={'tid':'7','qpc_start':'100','qpc_end':'1100','qpc_frequency':'1000000','deadline_us':'600'}
meta={'process_trace_result':0,'events_lost':0,'buffers_lost':0,'perf_frequency':1000000,'target_cswitch':3}
def event(t,old,new,state=1):return dict(qpc=t,old_tid=old,new_tid=new,old_state=state,old_wait_reason=0)
for state,label in [(1,'READY_PREEMPTION_SUFFICIENT'),(5,'WAITING_SUFFICIENT_NEEDS_STACK')]:
    intervals=Intervals([event(0,99,7),event(400,7,99,state),event(900,99,7),event(1200,7,99)])
    value=intervals.measure(row,meta)
    if not(value['scheduled_us']==500 and value['off_cpu_us']==500 and value['coverage_complete']):raise RuntimeError(value)
    if classify(row,value,True)!=label:raise RuntimeError('wrong causal split')
    if not classify(row,value,False).startswith('NOT_RUN'):raise RuntimeError('ignored failed control')
    for bad in [dict(meta,events_lost=1),dict(meta,perf_frequency=10)]:
        if intervals.measure(row,bad)['coverage_complete']:raise RuntimeError('ignored invalid ETW')
full=Intervals([event(0,99,7),event(2000,7,99)]).measure(row,meta)
if classify(row,full,True)!='SCHEDULED_RUNTIME_OVER_BUDGET_NOT_PURE_DSP_PROOF':raise RuntimeError('running labelled DSP or preemption')
missing=Intervals([event(0,99,7)]).measure(row,meta)
if missing['coverage_complete']:raise RuntimeError('invented missing boundary')
print('PASS analytic preemption/waiting/running controls, missing intervals, frequency and loss negative controls')
