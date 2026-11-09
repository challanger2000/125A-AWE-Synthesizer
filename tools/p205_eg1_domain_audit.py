#!/usr/bin/env python3
"""P205: offline, reproducible EG1 Hz/cents counterfactual audit.

Input is only measured P200 pitch-bin metadata extracted from two completed,
source-pinned CT4390 physical-reference Actions artifacts. Never download or
publish original SoundFont, ROM, FLAC, or sample bytes. No engine/DSP changes.

CRITICAL: The counterfactual changes ONLY the pitch-domain interpretation of
an INFERRED normalized progress x from the native baseline. It is not a new
renderer and does NOT prove that the underlying silicon uses either domain.
The empirical P203 shape is also checked for physical monotonicity.
"""
from __future__ import annotations
import argparse
import json
import math
import statistics as stats
from pathlib import Path

SCHEMA = "125A-P205-EG1-pitch-measured-points-v1"
EXPECTED_RUNS = {"baseline": (42685155427, 13703694431),
                 "slow_p203": (42685310513, 13705190866)}
D = 1200.0


def cents(f1: float, f2: float) -> float:
    return D * math.log2(f1 / f2)


def p203_curve(x: float) -> float:
    return 1 - (1 - x) ** 13.5 - .30 * x * (1 - x)


def original_curve(x: float) -> float:
    return 1 - (1 - x) ** 13.5


def metrics(error_cents: list[float]) -> dict:
    if not error_cents:
        raise ValueError("Empty metrics")
    return {"n": len(error_cents),
            "median_signed_cents": round(stats.median(error_cents), 3),
            "median_abs_cents": round(stats.median(map(abs, error_cents)), 3),
            "rmse_cents": round(math.sqrt(stats.mean(e * e for e in error_cents)), 3),
            "max_abs_cents": round(max(map(abs, error_cents)), 3)}


def validate(data: dict) -> None:
    if data.get("schema") != SCHEMA:
        raise ValueError("Unknown fixture schema")
    ref = data.get("original_reference", {})
    if (ref.get("model") != "AWE64 Gold CT4390 analog output"
            or ref.get("midi_note") != 59
            or ref.get("sample_id") != 43
            or ref.get("mod_env_to_pitch_cents") != 1200
            or ref.get("attack_mod_env_timecents") != 0
            or ref.get("delay_mod_env_timecents") != 0
            or ref.get("p97_coarse_lag_ms") != 0
            or ref.get("expected_p199_analysis_lag_ms") != 23
            or not all(len(ref.get(k, "")) == 40 for k in
                           ("original_sf2_git_blob", "original_midi_git_blob",
                            "original_reference_flac_git_blob"))):
        raise ValueError("Wrong source provenance or SF2 note59 fixture")
    cap = data.get("captures", {})
    if set(cap) != set(EXPECTED_RUNS):
        raise ValueError("Both pinned P200 CT4390 runs are required")
    for key, (rid, aid) in EXPECTED_RUNS.items():
        a = cap[key]
        if (a.get("run_id"), a.get("artifact_id")) != (rid, aid) or len(a.get("run_head_sha", "")) != 40:
            raise ValueError("Wrong original Actions run provenance for " + key)
        if not (730 < a["hold_reference_hz"] < 745 and
                730 < a["hold_native_hz"] < 745):
            raise ValueError("Wrong hardware/native hold pitch")
        rows = a.get("attack_rows", [])
        if len(rows) != 10 or [r["t"] for r in rows] != [round(10.64 + .08*i, 2) for i in range(10)]:
            raise ValueError("Missing or reordered original P200 bins")
        if not all(r["hw"] and r["hw"] > 0 for r in rows):
            raise ValueError("Hardware pitch tracking incomplete")
        if sum(r["native"] is not None for r in rows) != 9 or rows[0]["native"] is not None:
            raise ValueError("Invalid estimator-rejection boundaries")
    a, b = cap["baseline"], cap["slow_p203"]
    if (a["hold_reference_hz"],a["hold_native_hz"]) != (b["hold_reference_hz"], b["hold_native_hz"]):
        raise ValueError("Hold pitch moved between experiments")
    if [r["hw"] for r in a["attack_rows"]] != [r["hw"] for r in b["attack_rows"]]:
        raise ValueError("Physical recordings changed between experiments")


def measure(data: dict) -> dict:
    validate(data)
    result = {"experiment": "P205 offline EG1 domain falsification from original CT4390 P200 bins",
              "reference": data["original_reference"],
              "comparisons": {}, "p203_monotonicity": {},
              "decision": {},
              "limits": [
                  "Counterfactual Hz/Cent transforms use measured native pitch and inferred x; they do not render a modified EMU8000.",
                  "Normalized envelope progress assumes original note59 +1200-cent modulation and unchanged plateau pitch.",
                  "Only 9 valid 80ms-spaced attack windows; 96/160ms FFT averaging limits attack resolution.",
                  "One original AWE64 Gold CT4390 analog recording, one SF2 note; no independent chip readback or 0x0C register hardware sweep.",
                  "No time, pitch, gain, or filter fitting was performed; no original media or production files changed."]}
    for key, a in data["captures"].items():
        hold_n = a["hold_native_hz"]
        raw_error, hz_error, inverse_error, aligned_error = [], [], [], []
        bins=[]
        for r in a["attack_rows"]:
            if r["native"] is None:
                continue
            f_nat,f_hw = r["native"],r["hw"]
            # Effective progress x under the EXISTING, verified pitch-octave path:
            # at x=0 pitch f_hold/2, at x=1 pitch f_hold (+1200 cents).
            x = 1 + math.log2(f_nat / hold_n)
            if not (0 <= x <= 1.001):
                raise ValueError("Unexpected native normalized EG1 pitch progress: " + str(x))
            x = min(1.,max(0.,x))
            # Counterfactual Hz-linear transfer at the SAME inferred EG1 progress.
            f_hz = (hold_n / 2) * (1 + x)
            # Reverse transform is explicitly a hypothetical NOT the native model.
            x_if_hz = 2 * f_nat / hold_n - 1
            f_inverse = (hold_n / 2) * (2 ** x_if_hz)
            a0, a1, a2 = cents(f_nat,f_hw),cents(f_hz,f_hw),cents(f_inverse,f_hw)
            raw_error.append(a0)
            hz_error.append(a1)
            inverse_error.append(a2)
            aligned_error.append(cents(f_nat * a["hold_reference_hz"] / hold_n,f_hw))
            bins.append({"t_s":r["t"],"hardware_hz":f_hw,"native_hz":f_nat,
                         "native_inferred_cent_progress":round(x,6),
                         "hardware_inferred_cent_progress":round(1 + math.log2(f_hw / a["hold_reference_hz"]),6),
                         "hz_domain_counterfactual_hz":round(f_hz,3),
                         "native_minus_hardware_cents":round(a0,3),
                         "hz_domain_minus_hardware_cents":round(a1,3)})
        got = {"run_id":a["run_id"],"artifact_id":a["artifact_id"],
               "hold_hardware_hz":a["hold_reference_hz"],"hold_native_hz":hold_n,
               "hold_native_minus_hardware_cents":round(cents(hold_n,a["hold_reference_hz"]),3),
               "original_p200_median_abs_cents":a["p200_original_med_abs_cents"],
               "actual_native":metrics(raw_error),
               "counterfactual_cent_to_hz":metrics(hz_error),
               "counterfactual_hz_to_cent_inversion_not_native_model":metrics(inverse_error),
               "optional_hold_aligned_native_not_primary":metrics(aligned_error),
               "bins":bins}
        if abs(got["actual_native"]["median_abs_cents"]-a["p200_original_med_abs_cents"])>.03:
            raise ValueError("Recomputed P205 metric disagrees with original P200 oracle")
        result["comparisons"][key]=got
    # Verify the proposed experimental shape mathematically without audio.
    steps=10000
    samples=[i/steps for i in range(steps+1)]
    p203=[p203_curve(x) for x in samples]
    diffs=[p203[i+1]-p203[i] for i in range(steps)]
    bad=[i for i,d in enumerate(diffs) if d < -1e-9]
    if not all(original_curve(samples[i+1]) >= original_curve(samples[i])-1e-12
               for i in range(steps)):
        raise AssertionError("Original Block30 shape unexpectedly nonmonotone")
    p203row=data["captures"]["slow_p203"]["attack_rows"]
    pitch_dips=[{"from_s":u["t"],"to_s":v["t"],"from_hz":u["native"],"to_hz":v["native"],
                 "drop_cents":round(cents(u["native"],v["native"]),3)}
                for u,v in zip(p203row,p203row[1:])
                if u["native"] and v["native"] and v["native"] < u["native"]]
    result["p203_monotonicity"]={"p203_0_1_grid_steps":steps,
              "negative_slope_intervals":len(bad),
              "first_negative_progress_x":round(samples[bad[0]],5) if bad else None,
              "last_negative_progress_x":round(samples[bad[-1]+1],5) if bad else None,
              "steepest_negative_step":round(min(diffs),10),
              "original_13_5_curve_monotone":True,
              "actual_native_note59_pitch_dips":pitch_dips}
    if not bad or not pitch_dips:
        raise ValueError("P203 known attack nonmonotonicity was not reproduced")
    baseline=result["comparisons"]["baseline"]
    result["decision"]={
        "simple_cents_to_hz_counterfactual_improves_baseline_rmse":
            baseline["counterfactual_cent_to_hz"]["rmse_cents"] < baseline["actual_native"]["rmse_cents"],
        "p203_empirical_candidate_monotone":len(bad)==0,
        "production_dsp_change_justified":False,
        "reason":"Simple Hz reinterpretation worsens baseline RMSE; P203 native-only candidate creates nonmonotonic pitch on an increasing EG1 attack; neither establishes the real chip function."}
    print("P205 baseline RMSE actual %.3fc -> Hz-counterfactual %.3fc; median abs %.3fc -> %.3fc" %
          (baseline["actual_native"]["rmse_cents"],
           baseline["counterfactual_cent_to_hz"]["rmse_cents"],
           baseline["actual_native"]["median_abs_cents"],
           baseline["counterfactual_cent_to_hz"]["median_abs_cents"]))
    b=result["comparisons"]["slow_p203"]
    print("P205 P203 median abs %.3fc; nonmonotonic x intervals %d; real native pitch dips %s" %
          (b["actual_native"]["median_abs_cents"],len(bad),pitch_dips))
    return result


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--fixture",default="tests/fixtures/p205_eg1_ct4390_p200_points.json")
    ap.add_argument("--out",default=None)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        import copy
        x=.5
        assert abs(D*(math.log2(1+x)-x)-101.9550008654)<.001
        assert original_curve(.5)<1.00001
        sample=json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        validate(sample)
        for change in (lambda d:d["captures"]["baseline"].update(run_id=-1),
                       lambda d:d["captures"]["slow_p203"]["attack_rows"][3].update(hw=111.),
                       lambda d:d["original_reference"].update(mod_env_to_pitch_cents=600),
                       lambda d:d["captures"]["baseline"]["attack_rows"][4].update(native=None)):
            mutated=copy.deepcopy(sample)
            change(mutated)
            try:validate(mutated)
            except ValueError: pass
            else:raise AssertionError("P205 guard failed to reject mutated provenance/data")
        assert measure(sample)["decision"]["simple_cents_to_hz_counterfactual_improves_baseline_rmse"] is False
        print("P205 self-test: expected mathematics and 4 adversarial provenance/data mutations PASS")
        return
    data=json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    report=measure(data)
    if args.out:
        dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
