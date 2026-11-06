"""P140: independently analyze old P134 vs P137 same-runner ABBA/BAAB.

Preserve every measured real process() deadline miss. Distinguish full
population from exact-live-voice count and no invalid "0 misses = release".
This measures actual DLLs under a shared VM, but real ASIO/MMCSS is NOT RUN.
"""
from collections import defaultdict
from pathlib import Path
import csv
import json
import sys

if len(sys.argv)!=3:
    raise SystemExit("usage: p140_pair_compare.py PAIR_DIR OUTPUT.json")
root=Path(sys.argv[1])
output=Path(sys.argv[2])
order=("before-1","after-1","after-2","before-2")
wanted={0:3000,1:3000,2:3000,4:600,5:600}
summary=[]
per_mode=defaultdict(lambda:{"before":{"calls":0,"misses":0,"matched":0,"matched_misses":0,"median_samples":[],"p99_samples":[]},
                             "after":{"calls":0,"misses":0,"matched":0,"matched_misses":0,"median_samples":[],"p99_samples":[]}})
for name in order:
    fp=root/name/"summary.json"
    if not fp.is_file():raise SystemExit(f"Missing real VST3 sampled run: {fp}")
    data=json.loads(fp.read_text())
    if data.get("measured")!=sum(wanted.values()) or len(data.get("cases",[]))!=5:
        raise SystemExit(f"Undercounted P134/P137 same-runner load {name}: {data.get('measured')}")
    seen=set();counts={"all_misses":0,"matched_misses":0,"matched_n":0}
    for c in data["cases"]:
        if c["frames"]!=128 or c["voices"]!=30 or c["mode"] not in wanted:
            raise SystemExit(f"Different requested voices/periods in {name}: {c}")
        mode=c["mode"]
        if mode in seen or c["all"]["n"]!=wanted[mode]:
            raise SystemExit(f"Truncated/duplicate mode {mode} in {name}")
        seen.add(mode)
        arm="before" if name.startswith("before") else "after"
        g=per_mode[mode][arm]
        g["calls"]+=c["all"]["n"]
        g["misses"]+=c["all"]["overruns"]
        g["matched"]+=c["matched"]["n"]
        g["matched_misses"]+=c["matched"]["overruns"]
        if c["all"]["median_us"] is None or c["all"]["p99_us"] is None:
            raise SystemExit(f"Missing timed results in {name} mode {mode}")
        g["median_samples"].append(c["all"]["median_us"])
        g["p99_samples"].append(c["all"]["p99_us"])
        counts["all_misses"]+=c["all"]["overruns"]
        counts["matched_misses"]+=c["matched"]["overruns"]
        counts["matched_n"]+=c["matched"]["n"]
    if seen!=set(wanted):raise SystemExit(f"Missing modes in {name}: {set(wanted)-seen}")
    summary.append({"arm":name,"callbacks":sum(wanted.values()),**counts})
rows=[]
for mode in sorted(wanted):
    old,new=per_mode[mode]["before"],per_mode[mode]["after"]
    for name,g in (("P134",old),("P137",new)):
        if g["calls"]!=2*wanted[mode] or len(g["median_samples"])!=2 or len(g["p99_samples"])!=2:
            raise SystemExit(f"Missing completed paired case {mode}/{name}")
        rows.append({"mode":mode,"version":name,"calls":g["calls"],
                     "all_deadline_misses":g["misses"],
                     "load_matched_calls":g["matched"],
                     "load_matched_misses":g["matched_misses"],
                     "two_per_run_medians_us":g["median_samples"],
                     "two_per_run_p99_us":g["p99_samples"]})
before_total=sum(r["all_deadline_misses"] for r in rows if r["version"]=="P134")
after_total=sum(r["all_deadline_misses"] for r in rows if r["version"]=="P137")
before_matched=sum(r["load_matched_misses"] for r in rows if r["version"]=="P134")
after_matched=sum(r["load_matched_misses"] for r in rows if r["version"]=="P137")
evidence={
    "analysis":"P140 same-Windows-runner real VST3 ABBA paired P134-vs-P137; offline not ASIO",
    "base_archived_P135_v11_diagnostic_commit":"b249b110f1f0117e25757dc4001dc628d6b57d37",
    "optimized_P137_production_source_commit":"f0f397c265db4db145571b89d86676361d8514ae",
    "sample_rate":44100,"buffer_size":128,"physical_voices_requested":30,
    "load_modes":[0,1,2,4,5],"pairs":summary,"per_mode":rows,
    "before":{"all_callbacks":20400,"all_deadline_misses":before_total,"load_matched_deadline_misses":before_matched},
    "after":{"all_callbacks":20400,"all_deadline_misses":after_total,"load_matched_deadline_misses":after_matched},
    "real_time_verdict":"FAIL" if after_total else "PASS_ONLY_THESE_OFFLINE_WINDOWS_CASES",
    "cross_runner_statistics":"Not comparable with independent-P135/P139 runners without hardware matching",
    "ASIO":"NOT RUN","release_go":False
}
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(evidence,indent=2)+"\n")
with output.with_suffix(".csv").open("w",encoding="utf-8",newline="") as f:
    flat=[]
    for r in rows:
        d={k:v for k,v in r.items() if not isinstance(v,list)}
        d["median_run_1_us"],d["median_run_2_us"]=r["two_per_run_medians_us"]
        d["p99_run_1_us"],d["p99_run_2_us"]=r["two_per_run_p99_us"]
        flat.append(d)
    writer=csv.DictWriter(f,fieldnames=list(flat[0]))
    writer.writeheader();writer.writerows(flat)
print(f"P140_PAIRED_COMPLETE callbacks_old=20400 callbacks_new=20400 "
      f"old_misses={before_total} optimized_misses={after_total} "
      f"old_matched_misses={before_matched} optimized_matched_misses={after_matched} "
      f"optimized_rt_verdict={evidence['real_time_verdict']} ASIO=NOT_RUN RELEASE=NO_GO")
