"""Known intervals verify units, preemption attribution and fail-closed coverage."""
import csv,importlib.util,json,tempfile,sys
sys.dont_write_bytecode=True
from pathlib import Path
spec=importlib.util.spec_from_file_location('p132_analyze',Path(__file__).with_name('analyze.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def put(path,rows):
 with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp);(p/'etw').mkdir()
 # 1 MHz clock: a sleeping calibration [100,20100] with 100 us CPU;
 # busy control [30000,50000] entirely on CPU; genuine callback [60000,62000]
 # has only 500 us scheduled runtime and 1500 us preemption, budget 1000 us.
 def row(phase,a,b,matched='1'):
  return dict(phase=phase,qpc_begin=a,qpc_end=b,qpc_hz=1000000,tid=7,wall_us=b-a,frames=44.1,voices=1,mode=0,case=1,index=0,budget_us=1000,matched=matched,allocated_before=1,allocated_after=1,nonzero_before=1,nonzero_after=1,generation_before=1,generation_after=1)
 rows=[row('calibration_sleep',100,20100),row('calibration_busy',30000,50000),row('measure',60000,62000,'0')]
 # frames must be an integer; 44/44100 is near 1ms, budget explicitly 1000.
 for r in rows:r['frames']=44
 put(p/'callbacks.csv',rows)
 switches=[]
 def switch(t,old,new,state=1):switches.append(dict(qpc=t,cpu=0,old_tid=old,new_tid=new,old_state=state,old_wait_reason=0))
 for args in [(0,1,7),(200,7,1,5),(20100,1,7),(25000,7,1),(30000,1,7),(50000,7,1),(60000,1,7),(60200,7,1),(61700,1,7),(62000,7,1)]:switch(*args)
 put(p/'etw/cswitch.csv',switches)
 metadata=dict(perf_frequency=1000000,process_trace_result=0,events_lost=0,buffers_lost=0)
 (p/'etw/trace-meta.json').write_text(json.dumps(metadata))
 result=m.analyze(p)
 assert result['etw_context_valid'] and result['attributions']=={'PREEMPTION_SUFFICIENT':1}
 assert result['cases'][0]['all']['overruns']==1 and result['cases'][0]['matched']['n']==0,'underfilled deadline was hidden'
 assert not result['heap_backend_positive_control_complete'],'missing heap evidence was called PASS'
 metadata['events_lost']=1;(p/'etw/trace-meta.json').write_text(json.dumps(metadata));result=m.analyze(p)
 assert not result['etw_context_valid'] and result['attributions']=={'NOT_RUN_ETW_COVERAGE':1}
 print('PASS independent ETW interval, loss, heap-coverage and unmatched-deadline controls')
