"""P136: aggregate completed, pinned P135 real-VST3 RT measurements.

No new measurement, no PCM render and no production edits. Two independent
GitHub Actions artifacts have full raw traces. Revalidate both independently
before combining, and never call a failed RT workload a PASS.
"""
from collections import defaultdict
from pathlib import Path
import csv
import json
import sys

if len(sys.argv)!=4:
    raise SystemExit("usage: aggregate_p135_evidence.py RUNNER_A RUNNER_B OUTPUT")
roots=list(map(Path,sys.argv[1:3]))
output=Path(sys.argv[3])
expected_commit="b249b110f1f0117e25757dc4001dc628d6b57d37"
per_runner=[]
aggregate=defaultdict(lambda:dict(n=0,misses=0,matched=0,matched_misses=0,
                                   median_values=[],p99_values=[],max_us=0.0))
for trial,root in enumerate(roots,1):
    provenance=json.loads((root/"provenance.json").read_text())
    if provenance.get("commit")!=expected_commit or int(provenance.get("trial",0))!=trial:
        raise SystemExit(f"Source/runner provenance mismatch in {root}: {provenance}")
    if provenance.get("currentStateVersion")!="V11" or provenance.get("production_changed") is not False:
        raise SystemExit(f"Unexpected product variation / V11 status: {root}")
    counts=[]
    for field in ("traced","untraced"):
        doc=json.loads((root/field/"summary.json").read_text())
        if len(doc["cases"])!=72:
            raise SystemExit(f"{root} {field}: missing 72 independent cells")
        if field=="traced" and not doc["etw_context_valid"]:
            raise SystemExit(f"{root} CPU trace causality unavailable")
        for c in doc["cases"]:
            k=(field,int(c["mode"]))
            n=int(c["all"]["n"]); misses=int(c["all"]["overruns"])
            matched=int(c["matched"]["n"]);matched_misses=int(c["matched"]["overruns"])
            g=aggregate[k];g["n"]+=n;g["misses"]+=misses
            g["matched"]+=matched;g["matched_misses"]+=matched_misses
            if c["all"]["median_us"] is not None:g["median_values"].append(float(c["all"]["median_us"]))
            if c["all"]["p99_us"] is not None:g["p99_values"].append(float(c["all"]["p99_us"]))
            if c["all"]["max_us"] is not None:g["max_us"]=max(g["max_us"],float(c["all"]["max_us"]))
        counts.append({"pass":field,"measured":doc["measured"],"attributions":doc["attributions"],
                       "with_complete_ETW":bool(doc["etw_context_valid"]),
                       "calibration_sleep_off_us":doc["calibration_sleep_off_us"],
                       "calibration_busy_on_us":doc["calibration_busy_on_us"],
                       "etw_rows_with_incomplete_coverage":doc["etw_rows_with_incomplete_coverage"]})
    mem=json.loads((root/"memory"/"summary.json").read_text())
    if not mem["heap_backend_positive_control_complete"] or mem["memory_callbacks"]!=1440:
        raise SystemExit(f"Unqualified memory sample in {root}")
    if mem["memory_phase_heap_events"]!=0:
        raise SystemExit(f"Audio callbacks performed traced heap operations in {root}")
    with (root/"ctest.txt").open(encoding="utf-8",errors="replace") as f:
        t=f.read()
    if "100% tests passed, 0 tests failed out of 46" not in t:
        raise SystemExit(f"Missing independent 46/46 CTest evidence: {root}")
    with (root/"vst3-module-validator.txt").open(encoding="utf-8",errors="replace") as f:
        v=f.read()
    if "Result: 537 tests passed, 0 tests failed" not in v:
        raise SystemExit(f"Missing real VST3 537/537 validation: {root}")
    if not (root/"gui-verdict.json").exists():
        raise SystemExit("Three native GUI smokes unrecorded")
    gui=json.loads((root/"gui-verdict.json").read_text())
    if int(gui.get("completed",0))!=3:
        raise SystemExit(f"Not all 3 GUI smokes completed: {root}")
    per_runner.append({"trial":trial,"run_id":42227962225 if trial==1 else 42227962363,
                       "counts":counts,"heap_callbacks":1440,
                       "heap_events_in_audio":0,"ctest_passed":46,"validator_passed":537,"gui_passed":3})
rows=[]
for (pass_name,mode),g in sorted(aggregate.items()):
    rows.append({"pass":pass_name,"mode":mode,"callbacks":g["n"],
                 "deadline_overruns":g["misses"],"load_matched_callbacks":g["matched"],
                 "load_matched_overruns":g["matched_misses"],
                 "maximum_wall_us":round(g["max_us"],4),
                 # these are per-cell distributions, not pooled percentiles
                 "individual_cell_p99_max_us":max(g["p99_values"])})
original=[r for r in rows if r["mode"]<5]
extra=[r for r in rows if r["mode"]==5]
original_misses=sum(r["deadline_overruns"] for r in original)
extra_misses=sum(r["deadline_overruns"] for r in extra)
total=sum(r["deadline_overruns"] for r in rows)
calls=sum(r["callbacks"] for r in rows)
if calls!=201600 or sum(r["callbacks"] for r in original)!=172800 or sum(r["callbacks"] for r in extra)!=28800:
    raise SystemExit(f"Wrong full population {calls}, old={sum(r['callbacks'] for r in original)} new={sum(r['callbacks'] for r in extra)}")
result={
  "type":"P136 independent recheck of already recorded P135 real VST3 audio; NOT a re-run",
  "expected_production_source_commit":"e6a60ed154ee5a119b68a5ecd29d3f37961b9c4c",
  "measured_diagnostic_source_sha":expected_commit,
  "independent_windows_runners":per_runner,
  "outcomes_by_mode":rows,
  "original_P132_five_modes":{"callbacks":172800,
      "deadline_overruns":original_misses,
      "load_matched_deadline_overruns":sum(r["load_matched_overruns"] for r in original)},
  "new_FX_sixth_mode":{"callbacks":28800,
      "deadline_overruns":extra_misses,
      "load_matched_deadline_overruns":sum(r["load_matched_overruns"] for r in extra)},
  "total":{"callbacks":calls,"deadline_overruns":total,
           "load_matched_deadline_overruns":sum(r["load_matched_overruns"] for r in rows),
           "positive_controlled_audio_heap_events":0},
  "etw_legacy_P132_after_total_deadline_overruns":796,
  "comparison_caveats":"Different Windows shared-runner allocation; original 5 workloads are preserved but CC120 bugfix and P133 V11 present, so unpaired run totals are NOT same-hardware improvement evidence.",
  "realtime_lab_verdict":"FAIL" if total else "PASS_IN_WINDOWS_LAB_ONLY",
  "target_asio":"NOT RUN",
  "release_approved":False,
}
output.parent.mkdir(parents=True,exist_ok=True)
output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
with output.with_suffix(".csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(f"P136_VERIFIED source={expected_commit} windows_runners=2 "
      f"callbacks={calls} misses={total} original_five_mode_misses={original_misses} "
      f"added_fx_misses={extra_misses} heap=0 "
      f"real_time={result['realtime_lab_verdict']} ASIO=NOT_RUN RELEASE=NO_GO")
