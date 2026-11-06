"""P135: fail-closed numerical gate for both P134-V11 full realtime passes.

CI success means COMPLETENESS, not necessarily realtime PASS. No deadline
overrun is suppressed for underfilled or transition blocks. 44.1kHz fixed.
"""
from pathlib import Path
import json
import sys

root=Path(sys.argv[1])
expected={(fr,n,mode) for fr in (128,256,512,1024)
          for n in (1,16,30) for mode in range(6)}
results={}
for kind in ("traced","untraced"):
    path=root/kind/"summary.json"
    if not path.exists():
        raise SystemExit(f"P135 NOT RUN: {path} absent")
    data=json.loads(path.read_text())
    keys={(c["frames"],c["voices"],c["mode"]) for c in data["cases"]}
    if keys!=expected:
        raise SystemExit(f"P135 INCOMPLETE {kind}: missing {expected-keys}; extra {keys-expected}")
    n=0;overruns=0;matched_overruns=0;matched=0;mode5_overruns=0
    for c in data["cases"]:
        fr,voices,mode=c["frames"],c["voices"],c["mode"]
        wanted=3000 if fr==128 and voices==30 and mode<=2 else 600
        if c["all"]["n"]!=wanted:
            raise SystemExit(f"P135 INCOMPLETE {kind}: ({fr},{voices},{mode}) actual {c['all']['n']} not {wanted}")
        n+=c["all"]["n"];overruns+=c["all"]["overruns"]
        matched+=c["matched"]["n"];matched_overruns+=c["matched"]["overruns"]
        if mode==5:mode5_overruns+=c["all"]["overruns"]
        if c["matched"]["n"] > c["all"]["n"] or c["matched"]["overruns"]>c["all"]["overruns"]:
            raise SystemExit(f"P135 broken populations at {kind} ({fr},{voices},{mode})")
    if n!=50400:
        raise SystemExit(f"P135 INCOMPLETE {kind}: {n} callbacks not 50400")
    if kind=="traced":
        if not data["etw_context_valid"] or data["etw_rows_with_incomplete_coverage"]!=0:
            raise SystemExit("P135 ETW context absent, incomplete or lost: causal evidence NOT RUN")
    else:
        if data["etw_context_valid"]:
            raise SystemExit("P135 untraced population erroneously ETW-attributed")
    results[kind]={"callbacks":n,"all_deadline_misses":overruns,
                   "load_matched_callbacks":matched,
                   "load_matched_deadline_misses":matched_overruns,
                   "dense_fx_automation_deadline_misses":mode5_overruns,
                   "valid_etw_context":data["etw_context_valid"],
                   "offcpu_vs_oncpu_attributions":data["attributions"]}
memory=root/"memory"/"summary.json"
if not memory.exists():
    raise SystemExit("P135 memory stress not run")
mem=json.loads(memory.read_text())
if mem["memory_callbacks"]!=1440:
    raise SystemExit(f"P135 memory callbacks: expected 1440, got {mem['memory_callbacks']}")
if not mem["heap_backend_positive_control_complete"]:
    raise SystemExit("P135 heap controls not captured; no heap no-go/go can be concluded")
if mem["memory_phase_heap_events"]:
    raise SystemExit("P135 AUDIO THREAD HEAP EVENTS PRESENT: realtime violation")
results["heap"]={"audio_callback_count":mem["memory_callbacks"],
                 "heap_events_within_audio_callbacks":int(mem["memory_phase_heap_events"]),
                 "heap_positive_controls":mem["heap_positive_sizes"]}
results["totals"]={"measured_callbacks":sum(results[k]["callbacks"] for k in ("traced","untraced")),
                   "deadline_overruns":sum(results[k]["all_deadline_misses"] for k in ("traced","untraced")),
                   "matched_deadline_overruns":sum(results[k]["load_matched_deadline_misses"] for k in ("traced","untraced")),
                   "extra_fx_mode_deadline_overruns":sum(results[k]["dense_fx_automation_deadline_misses"] for k in ("traced","untraced"))}
results["test_basis"]="P134 merged + P133 V11, 44.1 kHz, real normal & diagnostic VST3, all 72 cells"
results["realtime_lab_verdict"]="FAIL" if results["totals"]["deadline_overruns"] else "PASS_IN_WINDOWS_LAB_ONLY"
results["target_asio"]="NOT RUN"
results["release_approved"]=False
(root/"p135-rt-verdict.json").write_text(json.dumps(results,indent=2)+"\n")
print("P135_MATRIX_COMPLETE",results["totals"],
      "REALTIME_LAB",results["realtime_lab_verdict"],
      "TARGET_ASIO=NOT_RUN RELEASE=NO_GO")
