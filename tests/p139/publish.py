"""Mirror compact numeric evidence as public CI annotations; retain raw artifacts.
No ETL bytes, process command lines, environment values or credentials are printed.
"""
from pathlib import Path
import base64,hashlib,json,re,sys,zlib,csv,statistics
root=Path(sys.argv[1]);payload={}
for name in ['traced','untraced','memory']+sorted(p.name for p in root.glob('paired-*') if p.is_dir()):
 p=root/name/'summary.json'
 if not p.exists():continue
 s=json.loads(p.read_text())
 # Public annotations have size/count limits. Full raw cycles/phase tables
 # remain in summary.json and CSV artifacts; retain all walltime populations.
 for c in s['cases']:
  for part in ['all','matched']:
   c[part]={k:v for k,v in c[part].items() if not k.startswith('cycles_')}
  if c['frames']!=128 or c['voices']!=30 or c['mode']>2:c.pop('adapter_980_boundary',None)
 s['control_cases']=[{k:v for k,v in r.items() if k in ['case','frames','voices','mode','saves','recalls','primings','control_error']} for r in s.get('control_cases',[])]
 s['worst']=[{k:r[k] for k in ['case','frames','voices','mode','wall_us','budget_us','matched','allocated_before','allocated_after','nonzero_before','nonzero_after','scheduled_us','ready_off_cpu_us','waiting_us','attribution']} for r in s['worst'][:10]]
 s['memory_phase_events']=s['memory_phase_events'][:10];payload[name]=s
for name in ['capabilities.json','provenance.json','gui-verdict.json','machine.json','qualification-all-sounds-off.json']:
 p=root/name
 if p.exists():payload[name]=json.loads(p.read_text())
errors=[]
for p in root.rglob('*.txt'):
 for line in p.read_text(errors='replace').splitlines():
  if re.search(r'error (?:C\d|LNK)|fatal error|CMake Error|P139_INCOMPLETE|P139_CONTROL_ERROR|Traceback|AssertionError|terminate|Exception',line):errors.append(str(p.relative_to(root))+': '+line[:1000])
ctest=(root/'ctest.txt').read_text(errors='replace') if (root/'ctest.txt').exists() else ''
validator=(root/'validator.txt').read_text(errors='replace') if (root/'validator.txt').exists() else ''
counts=re.findall(r'(\d+)% tests passed, (\d+) tests failed out of (\d+)',ctest)
payload['regression']={'ctest':counts[-1] if counts else None,'validator_47_pass':bool(re.search(r'Result:\s+47 tests passed,\s+0 tests failed',validator))}
q=root/'qualification-timing.csv'
if q.exists():
 groups={}
 for r in csv.DictReader(q.open()):groups.setdefault((r['frames'],r['voices']),[]).append(r)
 payload['normal_vs_diagnostic_timing']=[dict(frames=k[0],voices=k[1],n=len(v),normal_median_us=statistics.median(float(r['normal_wall_us']) for r in v),diagnostic_median_us=statistics.median(float(r['diagnostic_wall_us']) for r in v)) for k,v in groups.items()]
payload['diagnostics']=errors[:20]
payload['baseline_pcm']=(root/'before-after-pcm.txt').read_text() if (root/'before-after-pcm.txt').exists() else None
payload['host_progress']={str(p.relative_to(root)):p.read_text(errors='replace').splitlines()[-8:] for p in root.rglob('host-log.txt')}
raw=json.dumps(payload,separators=(',',':')).encode();data=base64.b64encode(zlib.compress(raw,9)).decode()
(root/'public-summary.json').write_bytes(raw)
chunks=[data[i:i+3000] for i in range(0,len(data),3000)]
print(f'P139_SUMMARY_SHA256={hashlib.sha256(raw).hexdigest()} CHUNKS={len(chunks)}')
for i,chunk in enumerate(chunks):print(f'::notice title=P139_EVIDENCE_{i+1}_OF_{len(chunks)}::P139_DATA_{i+1}_OF_{len(chunks)}_SHA_{hashlib.sha256(raw).hexdigest()}:{chunk}')
