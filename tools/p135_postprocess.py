"""P135 proof-only postprocessor for immutable A/B Windows Actions artifacts.

The P135 measurement jobs executed successfully, but the original end gate
mistakenly called len() on the INTEGER memory_phase_heap_events field.
This script only reads immutable artifacts and repeats the complete numerical
qualification; it cannot alter recordings, clock traces, sample data or the
producer DLL, and treats skipped measurements as NOT RUN.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

BASE_SHA = "b249b110f1f0117e25757dc4001dc628d6b57d37"
CASES = {(fr, n, mode) for fr in (128, 256, 512, 1024)
         for n in (1, 16, 30) for mode in range(6)}

def load(path):
    if not path.exists():
        raise ValueError(f"missing artifact evidence: {path}")
    return json.loads(path.read_text())

def validate(root, trial):
    p = root / "provenance.json"
    prov = load(p)
    if prov.get("commit") != BASE_SHA or prov.get("baselineCommit") != "e6a60ed154ee5a119b68a5ecd29d3f37961b9c4c":
        raise ValueError("wrong checked-out P134 V11 diagnostic source")
    if int(prov.get("trial", -1)) != trial or prov.get("production_changed") is not False:
        raise ValueError("wrong trial or production source was changed")
    ctest = (root / "ctest.txt").read_text(errors="replace")
    if not re.search(r"100% tests passed, 0 tests failed out of 46", ctest):
        raise ValueError("full 46/46 CTest regression not proven")
    for name in ("125A_p133_fx_processor_modes", "125A_p134_cc120_physical_stop", "125A_p135_diagnostic_dll_pcm_census", "125A_p135_measurement_oracle_controls"):
        if name not in ctest:
            raise ValueError(f"required physical/FX/ETW test not included: {name}")
    for name, count in (("validator.txt", 47), ("vst3-module-validator.txt", 537)):
        log = (root / name).read_text(errors="replace")
        if not re.search(rf"Result:\s+{count} tests passed,\s+0 tests failed", log):
            raise ValueError(f"Steinberg {name} incomplete")
    if load(root / "gui-verdict.json").get("completed") != 3:
        raise ValueError("GUI smoke tests not completed")
    qualification = (root / "qualification.txt").read_text(errors="replace").strip().splitlines()
    # The copied P132 host prints its historical lower-case metric label
    # state_v10_equal even though it serializes CURRENT AssetState V11 from
    # the P134 header. The tested bytes are V11; do not confuse labels with
    # wire-format version or silently skip the 12 real-DLL comparisons.
    if len(qualification) != 12 or not all(
        "pcm_bit_exact=1" in line and
        ("state_v10_equal=1" in line or "state_v11_equal=1" in line)
        for line in qualification
    ):
        raise ValueError("normal vs diagnostic P134 V11 chip/PCM qualification is incomplete")
    mem = load(root / "memory" / "summary.json")
    if mem.get("memory_callbacks") != 1440:
        raise ValueError("heap callbacks missing")
    if not mem.get("heap_backend_positive_control_complete"):
        raise ValueError("WPR Heap trace positive controls absent/lost")
    if set(mem.get("heap_positive_sizes", ())) < {37,73,91,131}:
        raise ValueError("heap allocations positive sizes not captured")
    if int(mem.get("memory_phase_heap_events", -1)) != 0:
        raise ValueError("actual audio callback malloc/realloc/HeapAlloc events present")
    passes={}
    for phase in ("traced","untraced"):
        d=load(root / phase / "summary.json")
        keys={(c["frames"],c["voices"],c["mode"]) for c in d["cases"]}
        if keys!=CASES or len(d["cases"]) != len(CASES):
            raise ValueError(f"{trial}/{phase} incomplete cases: {CASES-keys}")
        observed=0
        by_mode=collections.defaultdict(lambda:dict(callbacks=0,matched=0,all_misses=0,matched_misses=0))
        for c in d["cases"]:
            mode=c["mode"]
            n_expected=3000 if c["frames"]==128 and c["voices"]==30 and mode<=2 else 600
            if c["all"]["n"]!=n_expected:
                raise ValueError(f"wrong measured callback count at {trial}/{phase}/{c['frames']}/{c['voices']}/{mode}")
            if c["matched"]["n"]>c["all"]["n"] or c["matched"]["overruns"]>c["all"]["overruns"]:
                raise ValueError("matched population not a subset of all")
            observed+=n_expected
            g=by_mode[mode]
            g["callbacks"]+=c["all"]["n"];g["matched"]+=c["matched"]["n"]
            g["all_misses"]+=c["all"]["overruns"];g["matched_misses"]+=c["matched"]["overruns"]
        if observed!=50400 or d["measured"]!=50400:
            raise ValueError(f"{trial}/{phase} not 50400 callbacks")
        if phase=="traced":
            if not d["etw_context_valid"] or d["etw_rows_with_incomplete_coverage"] != 0:
                raise ValueError("ETW lost calibration or did not cover every callback")
        if phase=="untraced" and d["etw_context_valid"]:
            raise ValueError("untraced measurements incorrectly treated as ETW")
        passes[phase]=dict(callbacks=observed,
            all_misses=sum(v["all_misses"] for v in by_mode.values()),
            matched_misses=sum(v["matched_misses"] for v in by_mode.values()),
            original_5_modes=dict(
                callbacks=sum(by_mode[m]["callbacks"] for m in range(5)),
                all_misses=sum(by_mode[m]["all_misses"] for m in range(5)),
                matched_misses=sum(by_mode[m]["matched_misses"] for m in range(5))),
            new_fx_mode=dict(by_mode[5]),
            modes={str(k):v for k,v in sorted(by_mode.items())},
            validated_ETW=bool(d["etw_context_valid"]),
            attributions=d["attributions"],
            worst=d.get("worst",[])[:8],
            highlight_128_30={str(c["mode"]):{
                "all":c["all"],"matched":c["matched"],
                "underfilled":c["underfilled"],"generation_transitions":c["generation_transitions"]
                } for c in d["cases"] if c["frames"]==128 and c["voices"]==30})
    return dict(provenance=prov,trace=passes,heap=dict(callbacks=1440,events=0,
                controls=[37,73,91,131]),qualification=12,
                source_hashes_sha256=hashlib.sha256((root/"source-hashes.json").read_bytes()).hexdigest())

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--first",type=Path,required=True)
    a.add_argument("--second",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    args=a.parse_args()
    first=validate(args.first,1)
    second=validate(args.second,2)
    if first["source_hashes_sha256"]!=second["source_hashes_sha256"]:
        raise SystemExit("different production source fingerprints in two Windows allocations")
    results={"basis":"P134+P133 V11 merged production, P135 audit-only source",
             "sha":BASE_SHA,"independent_runners":{"A":first,"B":second}}
    passes=[p for run in (first,second) for p in run["trace"].values()]
    summary={
        "callbacks":sum(p["callbacks"] for p in passes),
        "deadline_overruns_all":sum(p["all_misses"] for p in passes),
        "deadline_overruns_matched":sum(p["matched_misses"] for p in passes),
        "p132_original_five_modes_callbacks":sum(p["original_5_modes"]["callbacks"] for p in passes),
        "p132_original_five_modes_misses":sum(p["original_5_modes"]["all_misses"] for p in passes),
        "p133_new_fx_mode_callbacks":sum(p["new_fx_mode"]["callbacks"] for p in passes),
        "p133_new_fx_mode_misses":sum(p["new_fx_mode"]["all_misses"] for p in passes),
        "heap_traced_audio_callbacks":2880,
        "heap_events_in_process":0,
        "validator_selftests":"47/47 per runner",
        "module_validation":"537/537 per runner",
        "ctest":"46/46 per runner",
        "gui":"3/3 per runner",
        "physical_asio":"NOT RUN",
        "realtime_lab_verdict":"FAIL" if any(p["all_misses"] for p in passes) else "PASS_WINDOWS_ONLY",
        "release_approved":False,
    }
    results["summary"]=summary
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(results,indent=2)+"\n")
    print("P135_POSTPROCESS_VALIDATED",json.dumps(summary,sort_keys=True))
    for name,run in (("A",first),("B",second)):
        for phase,p in run["trace"].items():
            print(f"P135_RUN {name} {phase} total={p['callbacks']} misses={p['all_misses']} "
                f"load_matched={p['matched_misses']} old_five_misses={p['original_5_modes']['all_misses']} "
                f"new_fx_mode_misses={p['new_fx_mode']['all_misses']} ETW={p['validated_ETW']} "
                f"attributions={p['attributions']}")
if __name__=="__main__":
    main()
