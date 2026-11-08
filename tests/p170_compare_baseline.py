"""Pinned pre-fix engine versus candidate, identical synthetic stimuli."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

old,new,folder=sys.argv[1:4];out=Path(folder);out.mkdir(parents=True,exist_ok=True)
script=Path(__file__).with_name('p170_audio_oracles.py')
for label,exe,expected in [('before',old,1),('after',new,0)]:
    run=subprocess.run([sys.executable,str(script),exe,str(out/label)],capture_output=True,text=True,timeout=600)
    (out/(label+'.txt')).write_text(run.stdout+run.stderr)
    if run.returncode!=expected:raise RuntimeError(f'{label} expected exit {expected}, got {run.returncode}\n'+run.stdout+run.stderr)
before=json.loads((out/'before/measurements.json').read_text())
after=json.loads((out/'after/measurements.json').read_text())
failures=[c['label'] for c in before['checks'] if not c['pass']]
for defect in ['<=50ms click','0->1%','FILTER ADSR','mode3 exits','endAddrsOffset']:
    if not any(defect in label for label in failures):raise RuntimeError('baseline did not reproduce '+defect)
compared=[];size=0
for row in after['rows']:
    if any(row['controls']) or row['label'] in ['loop-3','one-shot-end-offset']:continue
    a=(out/'before'/(row['label']+'.s16le')).read_bytes()
    b=(out/'after'/(row['label']+'.s16le')).read_bytes()
    if a!=b:raise RuntimeError('unintended neutral PCM change '+row['label'])
    size+=len(a);compared.append({'label':row['label'],'sha256':hashlib.sha256(a).hexdigest()})
if len(compared)<8:raise RuntimeError('incomplete neutral PCM comparison')
result={'baseline_defects':failures,'neutral_pcm_bitexact':compared,'compared_bytes':size}
(out/'comparison.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
