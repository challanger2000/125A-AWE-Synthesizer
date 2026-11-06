#!/usr/bin/env python3
"""Compare independently compiled real 86Box native-core A/B streams.
Check exact PCM and mirrored register fingerprints; summarize timing only as
shared-VM diagnostic. Refuse to label a candidate a validated optimization if
any audio or register byte differs.
"""
import csv
from pathlib import Path
import re
import sys

if len(sys.argv) != 4:
    raise SystemExit("usage: compare.py qa/ summary.csv verdict.txt")
root, output, verdict = map(Path,sys.argv[1:])
order=("baseline-a","candidate-a","candidate-b","baseline-b")
pattern=re.compile(
    r"DSP_AB case=(\S+) frames=(\d+) callbacks=(\d+) audible_blocks=(\d+)"
    r" mean_ms=([\d.]+) p99_ms=([\d.]+) max_ms=([\d.]+)"
    r" pcm_fnv64=([0-9a-fA-F]+) reg_fnv64=([0-9a-fA-F]+)"
)
records={}
for version in order:
    data={}
    for line in (root/f"{version}.txt").read_text().splitlines():
        match=pattern.search(line)
        if not match:continue
        case,frames,callbacks,heard,mean,p99,maximum,pcm,register=match.groups()
        key=(case,int(frames))
        if key in data:raise SystemExit(f"duplicate {version} {key}")
        if int(callbacks)!=400 or int(heard)<300:
            raise SystemExit(f"inaudible or insufficient callback controls in {version}: {key}")
        data[key]={"mean":float(mean),"p99":float(p99),"max":float(maximum),
                   "pcm":pcm,"register":register}
    if len(data)!=8:raise SystemExit(f"incomplete {version}: found {len(data)} cases")
    records[version]=data
rows=[]
all_exact=True
for key in sorted(records["baseline-a"]):
    same=all(records[name][key]["pcm"]==records["baseline-a"][key]["pcm"] and
             records[name][key]["register"]==records["baseline-a"][key]["register"]
             for name in order)
    all_exact&=same
    baseline=(records["baseline-a"][key]["mean"]+records["baseline-b"][key]["mean"])/2
    candidate=(records["candidate-a"][key]["mean"]+records["candidate-b"][key]["mean"])/2
    improvement=100.*(baseline-candidate)/baseline if baseline else 0.
    rows.append({"scenario":key[0],"frames":key[1],
                 "pcm_and_register_exact":same,
                 "baseline_avg_ms":round(baseline,5),
                 "candidate_avg_ms":round(candidate,5),
                 "candidate_speed_improvement_pct":round(improvement,2),
                 "baseline_pcm_fnv":records["baseline-a"][key]["pcm"],
                 "candidate_pcm_fnv":records["candidate-a"][key]["pcm"],
                 "baseline_reg_fnv":records["baseline-a"][key]["register"],
                 "candidate_reg_fnv":records["candidate-a"][key]["register"]})
    print("BOX86_AB",key[0],key[1],"exact=",same,
          "base=",round(baseline,4),"candidate=",round(candidate,4),
          "speedup_percent=",round(improvement,2))
with output.open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]))
    w.writeheader();w.writerows(rows)
with verdict.open("w") as f:
    f.write(f"PCM_AND_DRIVER_REGISTER_MIRROR_EXACT={all_exact}\n")
    f.write("SHARED_WINDOWS_RUNNER_TIMINGS_ARE_DIAGNOSTIC_NOT_ASIO_GO\n")
    f.write("VOICE_ALLOCATOR_AND_CHIP_DSP_REQUIRE_REAL_DAW_ACCEPTANCE\n")
if not all_exact:
    raise SystemExit("NOT MERGEABLE: PCM or mirror register mismatch")
print("BOX86_AB_EXACT: all eight scenarios bit-identical PCM and register mirror, 2 runs per variant")
