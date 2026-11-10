#!/usr/bin/env python3
"""P213 research: independently observed Win95 Creative Sustain vs source-derived
signed integer conversion on the specific P210/P212 additive preset fixture.
No new original measurements and no change to shipping VST3.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from copy import deepcopy
from decimal import Decimal,ROUND_HALF_EVEN

P210_RUN=42722686808
P212_RUN=42727927825
SOURCE_GIT_BLOB="4768c4a0215abf49c7a2bb51ada5ba3494faa1c5"
VXD_SHA="d343f2428ab3e593c9e42a668cf521b7801e1239792eaf7f2b11b5f179bc7c9a"
SF2_SHA="5ae0c05e37af073bd5d00c402ae33704303e69a0b917f07621158a16c57da6e2"
P212_INPUTS=(0,1,3,4,7,8,11,12,19,20,31,32,63,124,125,249,250,251,375,376,624,625,749,750,751,875,993,1000)
P210_SEEN={0,250,499,500,501,750,1000}
def check(ok,reason):
    if not ok:raise ValueError("P213 SOURCE-DERIVED SUSTAIN REJECT: "+reason)
def trunc0(num,den):
    check(type(num) is int and type(den) is int and den>0,"invalid x86 signed division")
    return (1 if num>=0 else -1)*(abs(num)//den)
def creative_convert(amount):
    check(type(amount) is int and -1000<=amount<=1000,"bounded original SF2 generator")
    # Verified actual 1998 SBAWE.VXD LE.object4 x86 instructions at
    # virtual object offset 0x3A33..0x3A44:
    # imul -127, cdq, idiv 1000 (truncate toward zero), add 127.
    return 127+trunc0(-127*amount,1000)
def fixture_two_stage(instrument,preset_delta):
    # Specifically observed original instrument 500 plus a separately
    # applied additive SF2 preset delta. Not generalized by assumption.
    result=creative_convert(instrument)+creative_convert(preset_delta)-127
    return min(127,max(0,result))
def p211_guess(n):
    return 127-int((Decimal(126*n)/Decimal(1000)).quantize(Decimal(1),rounding=ROUND_HALF_EVEN))
def audit(old,new):
    check(old.get("schema")=="P211-P210-genuine-Creative-derived-v1" and
          old.get("source_actions_run")==P210_RUN and
          old.get("source_public_original_sf2_git_blob")==SOURCE_GIT_BLOB,"P210 immutable provenance")
    check(new.get("schema")=="P213-P212-original-Creative-Sustain-locked-v1" and
          new.get("source_actions_run")==P212_RUN and
          new.get("source_artifact_id")==13724915362 and
          new.get("public_original_source_git_blob")==SOURCE_GIT_BLOB and
          new.get("original_vxd_sha256")==VXD_SHA and
          new.get("source_derived_sf2_sha256")==SF2_SHA and
          new.get("original_instrument_sustain")==500,"P212 original driver provenance")
    a,b=old["cases"],new["cases"]
    check(len(a)==14 and [v["program"] for v in a]==list(range(100,114)) and
          [v["sustain_permille"] for v in a]==[500]*8+[0,250,499,501,750,1000],
          "P210 population altered")
    check(len(b)==28 and [v["program"] for v in b]==list(range(100,128)) and
          tuple(v["sustain_permille"] for v in b)==P212_INPUTS,"P212 independent population altered")
    check(len(set(P212_INPUTS)-P210_SEEN)==24,"unseen value count changed")
    cases=[]
    for label,rows in (("P210",a),("P212",b)):
        for c in rows:
            s=c["sustain_permille"]
            actual=c["creative_sustain_high_byte"]
            check(type(actual) is int and 0<=actual<=127,"bad original sustain byte")
            predicted=fixture_two_stage(500,s-500)
            cases.append({"source":label,"program":c["program"],"sustain":s,
                          "original":actual,"predicted":predicted,"exact":actual==predicted})
    scores={name:sum(v["exact"] for v in cases if v["source"]==name) for name in ("P210","P212")}
    check(scores["P210"]==14 and scores["P212"]==28,
          "source-derived original signed integer pipeline fails independent Creative data")
    controls={0:127,250:95,750:33,1000:1}
    check({v["sustain_permille"]:v["creative_sustain_high_byte"] for v in b if v["sustain_permille"] in controls}==controls,
          "P212 original Creative repeat controls changed")
    guesses=sum(p211_guess(v["sustain_permille"])==v["creative_sustain_high_byte"] for v in b)
    check(guesses==22,"old P211 22/28 historical score changed")
    # These are mathematical properties only, not unmeasured original-driver oracle claims.
    all_values=[fixture_two_stage(500,n-500) for n in range(1001)]
    check(all_values[0]==127 and all_values[-1]==1 and
          all(all_values[i]>=all_values[i+1] for i in range(1000)),
          "source-derived fixture model unexpectedly non-monotonic")
    return {"schema":"P213-original-Creative-VXD-source-derived-research-v1",
            "source_binary_sha256":VXD_SHA,"source_code_location":"SBAWE.VXD LE.object4 0x3A33..0x3A44",
            "x86_operation":"127 + signed_trunc_toward_zero((-127*x)/1000)",
            "frozen_soundfont_semantics":"original instrument sustain 500 plus additive preset delta (desired-500)",
            "fixture_model":"creative_convert(500)+creative_convert(desired-500)-127",
            "verified_original_driver_cases":42,
            "P210_source_match":scores["P210"],"P212_source_match":scores["P212"],
            "distinct_observed_sustain_values":len({c["sustain"] for c in cases}),
            "older_P211_guess_matches_P212":guesses,
            "independent_P212_unseen_values":24,"source_data_fabricated":False,
            "new_original_Creative_driver_executed":False,
            "original_VXD_SF2_generator_29_full_call_path_traced":False,
            "other_instrument_base_values_tested":False,
            "physical_silicon_or_DAW_tested":False,
            "shipping_VST3_DSP_modified":False,
            "release_approval":"NO-GO"}
def selftest(old,new):
    result=audit(old,new)
    bad=deepcopy(new);bad["cases"][17]["creative_sustain_high_byte"]+=1
    for corrupt in (bad,{**new,"source_actions_run":0}):
        try:audit(old,corrupt)
        except ValueError:pass
        else:raise AssertionError("P213 intentionally corrupted evidence accepted")
    check(creative_convert(500)==64 and creative_convert(-250)==158 and
          fixture_two_stage(500,-250)==95 and fixture_two_stage(500,250)==33,
          "signed division and preset-delta witnesses")
    check(127+trunc0(-127*250,1000)==96,"direct interpretation witness changed")
    return result
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--p210",type=Path,required=True)
    p.add_argument("--p212",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=selftest(json.loads(a.p210.read_text()),json.loads(a.p212.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    print("P213 exact Creative VXD integer conversion with preserved additive SF2 preset staging: P210 14/14; P212 28/28; 31 unique values; 2 negative mutations rejected.")
    print("Research-only evidence; full original VXD generator call path, alternative instrument bases, physical AWE and DAW are NOT YET PROVEN.")
if __name__=="__main__":main()
