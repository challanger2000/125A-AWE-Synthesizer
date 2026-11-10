#!/usr/bin/env python3
"""P211: derived ORIGINAL Creative Windows 95 driver P210 EG1 sustain oracle.

One recorded driver sweep, seven distinct generator values, fourteen notes.
Mathematical hypothesis; no new original driver run, no EMU8000 silicon data,
no product DSP modification. The source P210 report remains the oracle.
"""
import argparse
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP
import json
from pathlib import Path

SOURCE_RUN = 42722686808
BLOB = "4768c4a0215abf49c7a2bb51ada5ba3494faa1c5"

def check(x, msg):
    if not x: raise ValueError("P211 REJECT: "+msg)

def predictions(permille):
    check(0 <= permille <= 1000, "SF2 sustain out of range")
    x = Decimal(permille)
    def rounded(scale, mode):
        return 127 - int((x*Decimal(scale)/Decimal(1000)).
                         quantize(Decimal(1), rounding=mode))
    return {
      "baseline_127_round_half_up": rounded(127,ROUND_HALF_UP),
      "p208_127_truncate": 127 - 127*permille//1000,
      "p211_126_round_ties_even": rounded(126,ROUND_HALF_EVEN),
      "126_round_half_up": rounded(126,ROUND_HALF_UP)
    }

def audit(d):
    check(d["schema"]=="P211-P210-genuine-Creative-derived-v1","unknown fixture")
    check(d["source_actions_run"]==SOURCE_RUN and
          d["source_public_original_sf2_git_blob"]==BLOB,
          "genuine original driver provenance mismatch")
    rows=d["cases"]
    check(len(rows)==14 and
          [r["program"] for r in rows]==list(range(100,114)),
          "wrong original 14-program source population")
    expected=[(100,500),(101,500),(102,500),(103,500),(104,500),
              (105,500),(106,500),(107,500),(108,0),(109,250),
              (110,499),(111,501),(112,750),(113,1000)]
    check([(r["program"],r["sustain_permille"]) for r in rows]==expected,
          "source test-domain changes were silently introduced")
    summaries={}
    for model in predictions(0):
        mismatch=[]
        for r in rows:
            computed=predictions(r["sustain_permille"])[model]
            if computed!=r["creative_sustain_high_byte"]:
                mismatch.append({"program":r["program"],
                  "sustain_permille":r["sustain_permille"],
                  "creative":r["creative_sustain_high_byte"],
                  "predicted":computed})
        summaries[model]={"matched":len(rows)-len(mismatch),
                          "mismatches":mismatch}
    check(summaries["baseline_127_round_half_up"]["matched"]==3,
          "old production C++ lround baseline did not reproduce P210")
    check(summaries["p208_127_truncate"]["matched"]==11,
          "P208 old native candidate did not reproduce P210")
    check(summaries["p211_126_round_ties_even"]["matched"]==14,
          "proposed 126-ties-even model fails genuine Creative driver")
    check(summaries["126_round_half_up"]["matched"]<14,
          "tie-rule evidence no longer discriminates candidate")
    check(len({r["sustain_permille"] for r in rows})==7,
          "test falsely claims more independent distinct generator values")
    return {"research":"P211 original Creative sustain integer-scale candidate",
       "original_Creative_driver_executed_in_this_workflow":False,
       "genuine_source":SOURCE_RUN,
       "actual_original_AWE64_silicon_sampled":False,
       "distinct_sustain_values":7,
       "total_original_driver_note_cases":14,
       "models":summaries,
       "hypothesis":"127 - round_ties_even(sustain_permille * 126 / 1000)",
       "proven":False,
       "unverified":"Any other generator values, negative/out-of-domain inputs, revisions, original VXD arithmetic",
       "product_VST3_DSP_unchanged":True,
       "status":"Research candidate; no product merge; no release approval"}

def selftest(data):
    got=audit(data)
    for mutator in (
      lambda d:d["cases"][9].update({"creative_sustain_high_byte":96}),
      lambda d:d["cases"][12].update({"creative_sustain_high_byte":32}),
      lambda d:d["cases"][13].update({"creative_sustain_high_byte":0}),
      lambda d:d["cases"].pop(),
      lambda d:d.update({"source_actions_run":0}),
      lambda d:d["cases"][10].update({"sustain_permille":500}),
    ):
        clone=json.loads(json.dumps(data))
        mutator(clone)
        try: audit(clone)
        except ValueError: pass
        else: raise RuntimeError("P211 adversarial source mutation undetected")
    # Boundary/rounding witness tests.
    check(predictions(250)["p211_126_round_ties_even"]==95,"250 witness")
    check(predictions(750)["p211_126_round_ties_even"]==33,"750 witness")
    check(predictions(1000)["p211_126_round_ties_even"]==1,"1000 witness")
    print("P211 self-tests: 6 rejected source mutations; tie/even/end witnesses PASS")
    return got

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--fixture",required=True)
    a.add_argument("--out",required=True)
    ns=a.parse_args()
    data=json.loads(Path(ns.fixture).read_text(encoding="utf8"))
    result=selftest(data)
    Path(ns.out).parent.mkdir(exist_ok=True,parents=True)
    Path(ns.out).write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    for name,r in result["models"].items():
        print(name, str(r["matched"])+"/14")
    print("P211 observed 14/14 within 7 distinct source values, research-only")
if __name__=="__main__":
    main()
