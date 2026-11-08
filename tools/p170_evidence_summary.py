"""Compact public numeric evidence; full raw PCM/CSV stays in CI artifacts."""
import base64
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import zlib

build,qa=map(Path,sys.argv[1:3]);qa.mkdir(parents=True,exist_ok=True)
cells={}
for row in csv.DictReader((build/'p171-rt.csv').open()):
    key=tuple(int(row[k]) for k in ('frames','notes','scenario'))
    cells.setdefault(key,[]).append(row)
stats=[]
for key,rows in sorted(cells.items()):
    times=sorted(float(r['wall_us']) for r in rows)
    stats.append(dict(zip(('frames','notes','scenario'),key),n=len(rows),
        median_us=statistics.median(times),p99_us=times[min(len(times)-1,int(len(times)*.99))],
        max_us=max(times),late=sum(int(r['late']) for r in rows),
        held_min=min(int(r['held_identities']) for r in rows),
        held_max=max(int(r['held_identities']) for r in rows)))
if len(stats)!=72 or any(s['n']!=200 for s in stats):raise RuntimeError('incomplete callback matrix')
audio=json.loads((build/'p170-audio/measurements.json').read_text())
paired=json.loads((build/'p170-paired/comparison.json').read_text())
ctest=(qa/'ctest.txt').read_text(encoding='utf-8-sig',errors='replace')
passed=re.search(r'100% tests passed, 0 tests failed out of (\d+)',ctest)
validator=(qa/'validator.txt').read_text(encoding='utf-8-sig',errors='replace')
validated=re.search(r'Result: (\d+) tests passed, 0 tests failed',validator)
if not passed or not validated:raise RuntimeError('full CTest/validator evidence absent')
modules=list((build/'VST3/Release/125A_AWE_Synthesizer.vst3').rglob('*.vst3'))
if len(modules)!=1:raise RuntimeError('ambiguous VST3 PE')
gui=json.loads((qa/'p165/result.json').read_text())
lab=json.loads((qa/'testlab/QUICKCHECK-RESULT.json').read_text())
summary={
    'source_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    'run_id':os.environ.get('GITHUB_RUN_ID'),'run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),
    'vst3_sha256':hashlib.sha256(modules[0].read_bytes()).hexdigest(),
    'ctests':int(passed[1]),'validator':int(validated[1]),
    'gui_passed':gui['passed'],'gui_checks':len(gui['results']),
    'lab_status':lab['status'],'lab_module_sha256':lab['verified_module_sha256'],
    'audio_checks':audio['checks'],'paired':paired,'rt_cells':stats,
    'measured_callbacks':sum(s['n'] for s in stats),'deadline_misses':sum(s['late'] for s in stats),
    'rt_scope':'offline shared Windows runner, no scheduler attribution; recall changes held load',
    'physical_asio':'NOT RUN','private_original_media':'NOT RUN',
    'etw':json.loads((qa/'etw-status.json').read_text(encoding='utf-8-sig')),
    'full_audit':'NOT COMPLETE','adversarial_review':'SELF_CHALLENGE','commercial_release':'NO-GO'}
csv_bytes=(build/'p171-rt.csv').read_bytes()
summary['raw_csv_sha256']=hashlib.sha256(csv_bytes).hexdigest()
# Preserve retrievable raw numeric rows in the run's folded job summary as
# well as in its artifact. This contains synthetic-test timings, no media.
job_summary=os.environ.get('GITHUB_STEP_SUMMARY')
if job_summary:
    packed=base64.b64encode(zlib.compress(csv_bytes,9)).decode()
    if len(packed)>800000:raise RuntimeError('raw timing summary exceeds safe summary size')
    with open(job_summary,'a',encoding='utf-8') as f:
        f.write('<details><summary>P170/P171 raw callback CSV (zlib/base64, SHA-256 verified)</summary>\n\n```text\n')
        f.write('P170_RAW_CSV_SHA_'+summary['raw_csv_sha256']+':'+packed+'\n```\n\n</details>\n')
data=json.dumps(summary,separators=(',',':')).encode()
(qa/'P170-P171-SUMMARY.json').write_bytes(data)
digest=hashlib.sha256(data).hexdigest();encoded=base64.b64encode(zlib.compress(data,9)).decode()
pieces=[encoded[i:i+2800] for i in range(0,len(encoded),2800)]
for i,part in enumerate(pieces):
    print(f'::notice title=P170 numeric evidence::P170_DATA_{i+1}_OF_{len(pieces)}_SHA_{digest}:{part}')
print(f"P170_SUMMARY CTEST={passed[1]} VALIDATOR={validated[1]} GUI={len(gui['results'])} LAB={lab['status']} DEADLINES={summary['deadline_misses']}/{summary['measured_callbacks']} RELEASE=NO-GO")
