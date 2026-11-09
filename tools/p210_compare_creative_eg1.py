#!/usr/bin/env python3
"""P210: evidence-driven 14-program genuine Win95 Creative vs two native cores.
Hypothesis mismatch = scientific finding, not infrastructure failure.
Driver original runs only in emulated guest; physical silicon not tested.
"""
import argparse
import hashlib
import json
from pathlib import Path
from p89_compare_voice_registers import original_csv,native_trace,compare

def require(ok,why):
    if not ok:raise ValueError("P210 EVIDENCE INVALID: "+why)
def word(seq,key):
    va=[val for _,name,val in seq if name==key]
    require(va and len(va)<=4,"missing/malformed original voice register "+key)
    return va
def selftest():
    arr=[{"program":i+100,"start_row":i*100,"end_row":(i+1)*100,
          "window_isolated":True} for i in range(14)]
    def valid(v):
        return len(v)==14 and [x["program"] for x in v]==list(range(100,114)) and all(
            x["window_isolated"] and x["end_row"]>x["start_row"] for x in v)
    require(valid(arr),"good 14-program sweep rejected")
    for bad in (arr[:-1], [{**x,"program":100} if x["program"]==104 else x for x in arr],
                [{**x,"end_row":x["start_row"]} if x["program"]==106 else x for x in arr]):
        require(not valid(bad),"negative cross-program trace mutation accepted")
    print("P210 self-test PASS: 3 negative source/provenance controls")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    for name in ("manifest","guest_report","guest_verification","creative_csv",
                 "native_base_dir","native_candidate_dir","out"):
        p.add_argument("--"+name.replace("_","-"),dest=name)
    a=p.parse_args()
    if a.self_test:
        selftest()
        if not a.manifest:return
    require(all(getattr(a,n) for n in ("manifest","guest_report","guest_verification",
                "creative_csv","native_base_dir","native_candidate_dir","out")),
            "missing independently captured authentic source inputs")
    manifest=json.loads(Path(a.manifest).read_text())
    guest=json.loads(Path(a.guest_report).read_text())
    verify=json.loads(Path(a.guest_verification).read_text())
    require(manifest["schema"]=="P210-cloned-original-EG1-v2" and
            manifest["synthetic_only"] is False and
            manifest["preserved_original_audio_samples"] and
            manifest["preserved_original_6_presets"] and
            manifest["public_original_source_git_blob"]==
                "4768c4a0215abf49c7a2bb51ada5ba3494faa1c5" and
            len(manifest["programs"])==14 and
            [p["program"] for p in manifest["programs"]]==list(range(100,114)),
            "not P207 Creative-accepted public original SF2 with controlled append-only additions")
    require(verify["agent_launched_in_actual_win95"] and
            verify["original_creative_winmm_endpoint_selected"] and
            verify["creatives_midi_short_messages_delivered"]>=56 and
            verify["audio_observed"] and not verify["win95_agent_error"],
            "genuine Creative MIDI+EMU8000 output not verified")
    trial=guest["p64_original_win95_midi"]
    require(trial.get("p210_real_win95_driver_sweep")==True,
            "only genuine P210 Win95 guest driver permitted")
    windows=trial["p210_original_creative_register_windows"]
    require(len(windows)==14 and
            [x["program"] for x in windows]==list(range(100,114)) and
            all(x["window_isolated"] and x["note"]==59 and x["velocity"]==100
                and x["end_row"]>x["start_row"] for x in windows),
            "fake, missing, repeated or out-of-order guest-note windows")
    cases=[]
    for v,w in zip(manifest["programs"],windows):
        pr=v["program"]
        require(pr==w["program"] and v["note"]==59,
                "source-derived generator not paired with original Creative trace")
        ref=original_csv(Path(a.creative_csv),w["start_row"],w["end_row"])
        nname=f"B0_P{pr}_N59_native-port-write.trace"
        b=native_trace(Path(a.native_base_dir)/nname)
        c=native_trace(Path(a.native_candidate_dir)/nname)
        require(len({voice for voice,_,_ in ref})==1 and
                len({voice for voice,_,_ in b})==1 and
                len({voice for voice,_,_ in c})==1,
                "voice stealing / overlapping note contaminated single-note oracle")
        origA,origS=word(ref,"ATKHLD"),word(ref,"DCYSUS")
        baseA,baseS=word(b,"ATKHLD"),word(b,"DCYSUS")
        candA,candS=word(c,"ATKHLD"),word(c,"DCYSUS")
        require(len(origA)==len(baseA)==len(candA)==1 and
                len(origS)==len(baseS)==len(candS)==2,
                "unexpected hold/sustain write count – must not cherry-pick")
        require(word(ref,"ENVVAL")==word(b,"ENVVAL")==word(c,"ENVVAL"),
                "delay register/driver path not comparable")
        require(word(ref,"PEFE")==word(b,"PEFE")==word(c,"PEFE"),
                "pitch-mod depth not equal")
        cmpb=compare(ref,b);cmpc=compare(ref,c)
        require(cmpb["register_series_compared"]>=29 and
                cmpc["register_series_compared"]>=29,
                "not comparable original driver note trace")
        cases.append({
          "program":pr,
          "hold_mod_env_tc":v["hold_mod_env_tc"],
          "sustain_mod_env_permille":v["sustain_mod_env_permille"],
          "original_atkhld":"0x%04X"%origA[0],
          "native_baseline_atkhld":"0x%04X"%baseA[0],
          "native_candidate_atkhld":"0x%04X"%candA[0],
          "original_dcysus":["0x%04X"%x for x in origS],
          "native_baseline_dcysus":["0x%04X"%x for x in baseS],
          "native_candidate_dcysus":["0x%04X"%x for x in candS],
          "hold_candidate_exact":origA==candA,
          "hold_baseline_exact":origA==baseA,
          "sustain_candidate_exact":origS==candS,
          "sustain_baseline_exact":origS==baseS,
          "native_baseline_series_equal":cmpb["register_series_exactly_equal"],
          "native_baseline_series_total":cmpb["register_series_compared"],
          "native_candidate_series_equal":cmpc["register_series_exactly_equal"],
          "native_candidate_series_total":cmpc["register_series_compared"],
          "driver_mismatch_names_baseline":[x["register"] for x in cmpb["mismatches"]],
          "driver_mismatch_names_candidate":[x["register"] for x in cmpc["mismatches"]]
        })
    require(len(cases)==14 and len({(x["hold_mod_env_tc"],x["sustain_mod_env_permille"]) for x in cases})==14,
            "generator sweep coverage loss")
    def stats(key):
        return sum(1 for x in cases if x[key])
    report={
      "schema":"P210-Creative-original-driver-EG1-sweep-v1",
      "authenticated_original_win95_creative_driver":True,
      "physical_AWE64_hardware_present":False,
      "original_soundfont":"P207 Creative-accepted public v3.0 source; fourteen appended preset-only variants using unchanged sample43.",
      "public_original_sf2_git_blob":manifest["public_original_source_git_blob"],
      "derived_sf2_sha256":manifest["sf2_sha256"],
      "original_instrument_sample_tables_preserved":True,
      "test_note":59,"velocity":100,
      "cases":cases,
      "hold_candidate_matches":stats("hold_candidate_exact"),
      "hold_baseline_matches":stats("hold_baseline_exact"),
      "sustain_candidate_matches":stats("sustain_candidate_exact"),
      "sustain_baseline_matches":stats("sustain_baseline_exact"),
      "hold_hypothesis_general_supported":stats("hold_candidate_exact")==14,
      "sustain_hypothesis_general_supported":stats("sustain_candidate_exact")==14,
      "conclusion":"Measured candidate parity; failure of hypothesis is an informative result, not a CI failure",
      "original_CT4390_0x0C_attack_fidelity":"NOT MEASURED by this driver-oracle-only experiment",
      "source_driver_register_oracle_only":True,
      "product_DSP_and_VST3_unchanged":True,
      "original_media_uploaded":False,
      "release":"NO-GO"}
    Path(a.out).write_text(json.dumps(report,indent=2)+"\n")
    print("P210 authentic Creative source-driver EG1 hold",report["hold_candidate_matches"],
          "/14 candidate vs",report["hold_baseline_matches"],"/14 baseline")
    print("P210 authentic Creative source-driver EG1 sustain",report["sustain_candidate_matches"],
          "/14 candidate vs",report["sustain_baseline_matches"],"/14 baseline")
    print("P210 14/14 genuine Win95 driver cases executed; physical CT4390 silicon remains UNVERIFIED")
if __name__=="__main__":main()
