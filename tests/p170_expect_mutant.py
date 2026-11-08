"""Require a specific audible defect, not a crash, setup error or timeout."""
import json
from pathlib import Path
import subprocess
import sys

kind,exe,out=sys.argv[1:4];directory=Path(out);directory.mkdir(parents=True,exist_ok=True)
if kind in ('bank','rom'):
    result=subprocess.run([exe],capture_output=True,text=True,timeout=90)
    failures=[line for line in result.stdout.splitlines() if line.startswith('FAIL ')]
    expected='P167 adversarial' if kind=='bank' else 'ROM attenuation PCM'
    valid=result.returncode==1 and len(failures)==1 and expected in failures[0]
else:
    result=subprocess.run([sys.executable,str(Path(__file__).with_name('p170_audio_oracles.py')),exe,str(directory)],
                          capture_output=True,text=True,timeout=600)
    expected={'amp':['<=50ms click','AMP decay audio sweep'],
              'filter':['filter'],'loop':['mode3 exits'],
              'end':['endAddrsOffset','endAddrsCoarseOffset'],
              'pedal':['mode3 exits only after sustain-pedal'],
              'headroom':['reverb retains audible headroom']}[kind]
    data=directory/'measurements.json'
    failures=[]
    if data.exists():
        failures=[c['label'] for c in json.loads(data.read_text())['checks'] if not c['pass']]
    valid=result.returncode==1 and bool(failures) and all(
        any(pattern.lower() in label.lower() for pattern in expected) for label in failures)
(directory/'stdout.txt').write_text(result.stdout+result.stderr)
print(json.dumps({'mutant':kind,'detected':valid,'exit':result.returncode,'failures':failures}))
sys.exit(0 if valid else 1)
