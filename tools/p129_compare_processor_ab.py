#!/usr/bin/env python3
"""A/B real product Processor timing. The *same* debug-free benchmark and
generated nonproprietary ROM/SF2 run in separately built P128 and P129 trees.
Four runs are interleaved B-C-C-B to weaken shared CI VM drift.
This cannot certify ASIO deadlines; report raw spread and tail failures.
"""
from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path
import statistics
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: p129_compare_processor_ab.py qa/ qa/summary.csv")
root, dest = map(Path, sys.argv[1:])
order = ("baseline-a", "candidate-a", "candidate-b", "baseline-b")
SCENARIOS = tuple((frames, case) for frames in (128, 256, 1024)
                  for case in ("render", "save", "save_recall"))
records = {}
for version in order:
    path = root / f"{version}.csv"
    if not path.is_file():
        raise SystemExit(f"Missing callback data: {path}")
    grouped = defaultdict(list)
    with path.open(newline="", encoding="utf-8-sig") as source:
        for r in csv.DictReader(source):
            key = (int(r["frames"]), r["case"])
            grouped[key].append(r)
    if set(grouped) != set(SCENARIOS):
        raise SystemExit(f"Scenario mismatch in {version}: {set(grouped)}")
    for key, values in grouped.items():
        if len(values) != 250 or sorted(int(x["callback"]) for x in values) != list(range(250)):
            raise SystemExit(f"Missing/repeated callbacks: {version} {key}")
        if sum(int(x["audible_pcm"]) for x in values) < 200:
            raise SystemExit(f"Unexpectedly silent audio: {version} {key}")
    records[version] = grouped

def stats(rows, frames):
    times = sorted(float(x["process_ms"]) for x in rows)
    budget = 1000.0 * frames / 44100.0
    def percentile(p):
        return times[max(0, int((p * len(times) + 0.999999999)) - 1)]
    return {
        "median_ms": statistics.median(times),
        "p95_ms": percentile(.95),
        "p99_ms": percentile(.99),
        "max_ms": max(times),
        "overruns": sum(t > budget for t in times),
        "scheduling_misses": sum(int(x["missed_scheduled_deadline"]) for x in rows),
        "audible": sum(int(x["audible_pcm"]) for x in rows)
    }

rows_out = []
for frames, case in SCENARIOS:
    variants = {name:stats(records[name][(frames, case)], frames) for name in order}
    base_med = statistics.median([variants[k]["median_ms"] for k in ("baseline-a", "baseline-b")])
    cand_med = statistics.median([variants[k]["median_ms"] for k in ("candidate-a", "candidate-b")])
    gain = 100.0 * (base_med - cand_med)/base_med if base_med else 0.0
    row = {"frames":frames,"scenario":case,
           "audio_budget_ms":round(1000.0*frames/44100.0, 4),
           "baseline_median_ms":round(base_med, 6),
           "p129_median_ms":round(cand_med, 6),
           "p129_median_improvement_pct":round(gain, 3)}
    for name in order:
        for measure in ("p95_ms","p99_ms","max_ms","overruns","scheduling_misses","audible"):
            row[f"{name}_{measure}"] = variants[name][measure]
    rows_out.append(row)
    print(f"PROCESS_AB frames={frames} mode={case} baseline_median={base_med:.4f}ms "
          f"p129_median={cand_med:.4f}ms change={gain:+.2f}% "
          f"baseline_overruns={variants['baseline-a']['overruns']+variants['baseline-b']['overruns']}/500 "
          f"p129_overruns={variants['candidate-a']['overruns']+variants['candidate-b']['overruns']}/500 "
          f"baseline_p99_a={variants['baseline-a']['p99_ms']:.4f} "
          f"p129_p99_a={variants['candidate-a']['p99_ms']:.4f}")
with dest.open("w", newline="") as target:
    writer = csv.DictWriter(target, fieldnames=list(rows_out[0]))
    writer.writeheader()
    writer.writerows(rows_out)
print("PROCESS_AB_COMPLETED: 9000 callback samples across two P128, two P129 "
      "processor runs; all nine audible scenarios validated")
print("SCOPE: source-extracted actual Factory.cpp Processor; same 86Box ROM/SF2; "
      "shared Windows-2022 VM; ASIO/DAW release pass NOT tested")
