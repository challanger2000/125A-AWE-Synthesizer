#!/usr/bin/env python3
"""P236 CT4390 physical-AWE64 benchmark: pinned old-vs-current 125A regression.

Two native binaries render the SAME hash-verified real CT4390 test MIDI/SF2,
then the UNMODIFIED P97 hardware comparator measures each against the SAME
actual physical CT4390 analog FLAC. No level/sample/preset hacks; the
comparator's historic single global gain fit is retained explicitly, and
raw level residuals are independently evaluated for each section.

Does not certify 1:1 hardware fidelity, waveform equality or provenance of
unmeasured AWETEST v25–28 tests. A GitHub SUCCESS is not acceptance.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

# PREDECLARED before reading a current result. This is a regression
# threshold, not proof of sufficient physical-hardware fidelity.
REGRESSION_LIMITS = {
    "section_raw_rms_abs_error_increase_db": 1.0,
    "section_gain_matched_band_abs_error_increase_db": 1.5,
    "global_gain_matched_band_abs_error_increase_db": 1.5,
    "section_envelope_correlation_decrease": 0.025,
    "global_envelope_correlation_decrease": 0.025,
}
SECTION_GROUP = {
    "01_volume_envelope": "amp_envelope",
    "02_modulation_envelope": "mod_envelope",
    "03_keynum_to_decay": "amp_envelope",
    "04_keynum_to_hold": "amp_envelope",
    "05_modulation_lfo": "modulation",
    "06_vibrato_lfo": "modulation",
    "07_modwheel": "modulation",
    "08_scale_tune": "pitch",
    "09_filter_cutoff": "filter",
    "10_filter_resonance": "filter",
    "11_attenuation": "headroom_gain",
    "12_negative_attenuation": "headroom_gain",
    "13_velocity_attenuation": "headroom_gain",
    "14_velocity_filter": "filter",
    "15_cc1_filter": "filter",
    "16_sample_offset": "sample",
    "17_reverb": "reverb",
    "18_chorus": "chorus",
    "19_interpolation": "interpolation",
    "20_pitch_bend": "pitch",
    "21_exclusive_class": "voice_release",
}
def require(ok,msg):
    if not ok:raise ValueError("P236_HARDWARE_EVIDENCE_INVALID: "+msg)
def level_error_db(section):
    a=float(section["hardware_rms"])
    b=float(section["native_rms"])
    require(a>0 and b>0,"silent or zero-RMS section")
    return 20*math.log10(b/a)
def bandmap(rows):
    result={}
    for r in rows:
        k=r["band_hz"]
        require(k not in result,"duplicate band")
        result[k]=float(r["native_minus_real_db_level_matched"])
    return result
def compare(old,cur,baseline_sha,current_sha):
    require(old.get("experiment")==cur.get("experiment") and
            "CT4390" in old.get("experiment",""),"not matching CT4390 hardware tests")
    require(old.get("compared_seconds")==cur.get("compared_seconds")==264,
            "not the same 264-second v3.0 source fixture")
    require(old.get("aligned_audio_seconds")>=260 and cur.get("aligned_audio_seconds")>=260,
            "missing actual full hardware audio coverage")
    require(old.get("source_recording")==cur.get("source_recording"),"hardware source description changed")
    bo,bc=bandmap(old["band_spectrum"]),bandmap(cur["band_spectrum"])
    require(set(bo)==set(bc),"global spectrum has mismatched bands")
    ro={v["test"]:v for v in old["sections"]}
    rc={v["test"]:v for v in cur["sections"]}
    require(set(ro)==set(rc) and len(ro)>=18,"mismatched/partial physical test sections")
    checks=[]
    def add(scope,kind,old_value,cur_value,limit,is_corr=False):
        increase=(old_value-cur_value) if is_corr else (abs(cur_value)-abs(old_value))
        checks.append({"scope":scope,"measurement":kind,
            "old":round(old_value,5),"current":round(cur_value,5),
            "error_increase":round(increase,5),"tolerance":limit,
            "regressed":increase>limit})
    for key in sorted(bo):
        add("whole_264s","gain_matched_band_"+key,bo[key],bc[key],
            REGRESSION_LIMITS["global_gain_matched_band_abs_error_increase_db"])
    add("whole_264s","log_rms_envelope_correlation",
        float(old["rms_envelope_log_correlation"]),
        float(cur["rms_envelope_log_correlation"]),
        REGRESSION_LIMITS["global_envelope_correlation_decrease"],True)
    sections=[]
    for name in sorted(ro):
        a,b=ro[name],rc[name]
        require(a["time_s"]==b["time_s"],f"{name} changed test time range")
        require(abs(float(a["hardware_rms"])-float(b["hardware_rms"]))<=1e-8,
                f"{name} not the same hardware reference recording (RMS differs)")
        old_level=level_error_db(a);cur_level=level_error_db(b)
        add(name,"raw_no_gain_adjust_native_minus_hardware_RMS_db",
            old_level,cur_level,
            REGRESSION_LIMITS["section_raw_rms_abs_error_increase_db"])
        oa,ca=bandmap(a["band_spectrum"]),bandmap(b["band_spectrum"])
        require(set(oa)==set(ca),f"{name} band mismatch")
        for key in sorted(oa):
            add(name,"gain_matched_band_"+key,oa[key],ca[key],
                REGRESSION_LIMITS["section_gain_matched_band_abs_error_increase_db"])
        add(name,"rms_envelope_log_correlation",
            float(a["rms_envelope_log_correlation"]),
            float(b["rms_envelope_log_correlation"]),
            REGRESSION_LIMITS["section_envelope_correlation_decrease"],True)
        sections.append({"section":name,"subsystem":SECTION_GROUP.get(name,"other"),
            "physical_hardware_rms":a["hardware_rms"],
            "baseline_native_rms":a["native_rms"],
            "current_native_rms":b["native_rms"],
            "baseline_raw_native_minus_hardware_db":round(old_level,4),
            "current_raw_native_minus_hardware_db":round(cur_level,4),
            "baseline_envelope_corr":a["rms_envelope_log_correlation"],
            "current_envelope_corr":b["rms_envelope_log_correlation"],
            "baseline_global_gain_matched_band_diffs":oa,
            "current_global_gain_matched_band_diffs":ca})
    regressions=[c for c in checks if c["regressed"]]
    improvements=[c for c in checks if c["error_increase"] < -c["tolerance"]]
    return {
        "schema":"125A-P236-physical-CT4390-regression-v1",
        "physical_reference":"SoundFont Spec Test v3.0 genuine AWE64 Gold CT4390 analog 48kHz, same hash-pinned FLAC/SF2/MIDI",
        "baseline_hardware_checked_commit":baseline_sha,
        "current_125a_commit":current_sha,
        "thresholds_predeclared":REGRESSION_LIMITS,
        "not_a_bitwise_hardware_test":True,
        "old_compatibility":old.get("native"),
        "current_compatibility":cur.get("native"),
        "baseline_hardware_gain_fit_db":old.get("hardware_to_native_global_gain_match_db"),
        "current_hardware_gain_fit_db":cur.get("hardware_to_native_global_gain_match_db"),
        "baseline_global_envelope_corr":old["rms_envelope_log_correlation"],
        "current_global_envelope_corr":cur["rms_envelope_log_correlation"],
        "compared_sections":sections,
        "comparisons_evaluated":len(checks),
        "regressions":regressions,
        "improvements":improvements,
        "regression_gate":"FAIL" if regressions else "PASS",
        "hardware_fidelity_accepted":"BLOCKED",
        "reason":"Physical analog AWE64 Gold capture has ADC/analog path and FX-state uncertainty; significant residuals require subsystem proof. Other AWETEST physical traces separately required.",
        "no_product_dsp_modified_by_test":True,
        "release":"NO-GO",
    }
def self_test():
    orig={"experiment":"CT4390 physical","compared_seconds":264,
        "aligned_audio_seconds":263.5,"source_recording":"pinned physical CT4390",
        "band_spectrum":[{"band_hz":"50-200","native_minus_real_db_level_matched":2}],
        "rms_envelope_log_correlation":.95}
    orig["sections"]=[{"test":k,"time_s":[i,i+1],
      "hardware_rms":.2,"native_rms":.2,"rms_envelope_log_correlation":.98,
      "band_spectrum":[{"band_hz":"50-200","native_minus_real_db_level_matched":1}]}
      for i,k in enumerate(SECTION_GROUP)]
    equal=compare(orig,orig,"BASE","NOW")
    assert equal["regression_gate"]=="PASS"
    x=json.loads(json.dumps(orig));x["sections"][0]["native_rms"]*=1.5
    assert compare(orig,x,"BASE","NOW")["regression_gate"]=="FAIL"
    y=json.loads(json.dumps(orig));y["sections"][1]["rms_envelope_log_correlation"]-=.04
    assert compare(orig,y,"BASE","NOW")["regression_gate"]=="FAIL"
    z=json.loads(json.dumps(orig));z["band_spectrum"][0]["native_minus_real_db_level_matched"]=4
    assert compare(orig,z,"BASE","NOW")["regression_gate"]=="FAIL"
    d=json.loads(json.dumps(orig));d["sections"][2]["hardware_rms"]=.1
    try:compare(orig,d,"BASE","NOW")
    except ValueError:pass
    else:raise AssertionError("reference substitution accepted")
    print("P236_CT4390_REGRESSION_SELF_TEST_PASS equal_positive=1 fault_injections=4")
def main():
    p=argparse.ArgumentParser()
    for k in ("old","current","out","summary","baseline-commit","current-commit"):
        p.add_argument("--"+k,required=False)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:return self_test()
    for key in ("old","current","out","summary","baseline_commit","current_commit"):
        require(getattr(a,key),f"missing CLI input {key}")
    out=Path(a.out);require(not out.exists(),"refuse overwriting immutable evidence")
    result=compare(json.loads(Path(a.old).read_text()),
                   json.loads(Path(a.current).read_text()),
                   a.baseline_commit,a.current_commit)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    rows=[
        "# P236 current-vs-2026-11-04 actual CT4390 hardware regression",
        f"Baseline {a.baseline_commit}; current {a.current_commit}",
        f"**{result['regression_gate']} regression gate**; hardware acceptance **BLOCKED**, not a release PASS.",
        f"Compared: {len(result['compared_sections'])} original physical test sections, {result['comparisons_evaluated']} metric pairs.",
        f"Regressions: {len(result['regressions'])}; significant improvements: {len(result['improvements'])}.",
        "",
        "| Section | Subsystem | Old raw RMS diff dB | New raw RMS diff dB | Old envelope r | New envelope r |",
        "|---|---|---:|---:|---:|---:|"]
    for s in result["compared_sections"]:
        rows.append(f"| {s['section']} | {s['subsystem']} | {s['baseline_raw_native_minus_hardware_db']:+.3f} | {s['current_raw_native_minus_hardware_db']:+.3f} | {s['baseline_envelope_corr']} | {s['current_envelope_corr']} |")
    rows.extend(["","## Regression events"])
    rows.extend([f"- {x['scope']}: {x['measurement']} old {x['old']} vs current {x['current']} (increase {x['error_increase']}, max {x['tolerance']})" for x in result["regressions"]])
    rows.append("The comparator's historical global gain fit is reported but is not a permitted per-preset correction.")
    Path(a.summary).write_text("\n".join(rows)+"\n")
    print("P236_TRUE_CT4390_OLD_VS_CURRENT",result["regression_gate"],
          "regressions",len(result["regressions"]),
          "improvements",len(result["improvements"]),
          "comparisons",result["comparisons_evaluated"],
          "hardware-acceptance=BLOCKED",flush=True)
    for s in result["compared_sections"]:
        if s["subsystem"] in ("filter","amp_envelope","mod_envelope","reverb","chorus","interpolation","headroom_gain"):
            print("P236_HARDWARE_SUBSYSTEM",s["section"],
                  "old_raw_RMS",s["baseline_raw_native_minus_hardware_db"],
                  "current_raw_RMS",s["current_raw_native_minus_hardware_db"],
                  "old_env",s["baseline_envelope_corr"],
                  "current_env",s["current_envelope_corr"],flush=True)
    if result["regressions"]:
        raise SystemExit("P236_TRUE_CT4390_HARDWARE_REGRESSION_BLOCKED")
if __name__=="__main__":main()
