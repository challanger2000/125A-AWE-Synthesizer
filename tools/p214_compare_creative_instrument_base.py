#!/usr/bin/env python3
"""P214 strict new original Creative Win95 register oracle for crossed instrument
and preset Sustain generators. Research result may falsify source-derived model.
No expected original-driver high bytes are created by this comparator.
"""
from __future__ import annotations
import argparse,hashlib,json
from copy import deepcopy
from pathlib import Path

from p89_compare_voice_registers import original_csv
from p210_compare_creative_eg1 import word
from p214_clone_instrument_matrix import BASES,TARGETS,PROGRAMS,CASES,SCHEMA,require_matrix
from p210_clone_verified_sf2 import SOURCE_GIT_BLOB

REPEATED_BASE500={0:127,1:127,249:95,250:95,500:64,750:33,1000:1}
ORIGINAL_VXD_SHA256="d343f2428ab3e593c9e42a668cf521b7801e1239792eaf7f2b11b5f179bc7c9a"

def require(ok,why):
    if not ok:raise ValueError("P214 ORIGINAL CREATIVE INDEPENDENT ORACLE INVALID: "+why)

def trunc0(n,d):
    require(type(n) is int and type(d) is int and d>0,"bad x86 signed division")
    return (1 if n>=0 else -1)*(abs(n)//d)

def T(n):
    require(type(n) is int and -1000<=n<=1000,"out of generator conversion domain")
    return 127+trunc0(-127*n,1000)

def source_derived(base,delta):
    return max(0,min(127,T(base)+T(delta)-127))

def validate_sources(manifest,guest,verify):
    require_matrix()
    require(manifest.get("schema")==SCHEMA and
            manifest.get("public_original_source_git_blob")==SOURCE_GIT_BLOB and
            manifest.get("original_six_presets_preserved") is True and
            manifest.get("original_25_instruments_preserved") is True and
            manifest.get("original_44_sample_records_preserved") is True and
            manifest.get("original_audio_pcm_byte_identical") is True and
            manifest.get("original_media_published") is False and
            manifest.get("instrument_bases")==list(BASES) and
            manifest.get("requested_sustain_values")==list(TARGETS),
            "not derived from the original Creative-accepted public bank")
    cases=manifest.get("cases",[])
    require(len(cases)==28 and
            [(x.get("program"),x.get("base_instrument_sustain"),
              x.get("sustain_mod_env_permille")) for x in cases]==list(CASES),
            "crossed instrument vs preset program generator matrix not frozen")
    require(all(c.get("preset_sustain_delta")==c["sustain_mod_env_permille"]-c["base_instrument_sustain"] and
                c.get("sample_id")==43 and c.get("note")==59 and
                c.get("velocity")==100 and c.get("hold_mod_env_tc")==0
                for c in cases),"original source sample/preset generator mapping changed")
    require(verify.get("agent_launched_in_actual_win95") is True and
            verify.get("original_creative_winmm_endpoint_selected") is True and
            verify.get("original_creative_com1_ready") is True and
            not verify.get("win95_agent_error") and
            verify.get("creatives_midi_short_messages_delivered",0)>=112 and
            verify.get("audio_observed") is True and
            verify.get("p84_universal_sf2_test") is True,
            "not authentic Win95 Creative WinMM MIDI, original driver and PCM")
    require(guest.get("hardware")=="sbawe64_gold" and
            guest.get("sample_ram_kib")==28672 and
            guest.get("p84_universal_sf2_test") is True and
            guest.get("p75_private_sample_upload_plausible") is True and
            guest.get("p75_private_sample_upload_write_words",0)>=
                guest.get("p75_private_sample_upload_minimum_words",1),
            "original Creative AWE64 Gold / SF2 upload authenticity missing")
    trial=guest.get("p64_original_win95_midi",{})
    require(trial.get("p214_real_win95_driver_sweep") is True and
            not trial.get("p212_real_win95_driver_sweep") and
            not trial.get("p210_real_win95_driver_sweep") and
            trial.get("p74_uart_frames_injected",0)>=112,
            "P214 run was replayed from P210/P212 or guest UART not exercised")
    windows=trial.get("p214_original_creative_register_windows",[])
    require(len(windows)==28 and [x.get("program") for x in windows]==list(PROGRAMS),
            "invalid or missing original Creative source windows")
    end=-1
    for w in windows:
        start,stop=w.get("start_row"),w.get("end_row")
        require(type(start) is int and type(stop) is int and
                start>=end and stop>start and
                w.get("window_isolated") is True and
                w.get("note")==59 and w.get("velocity")==100,
                "overlapping, nonisolated or wrong-note source trace")
        end=stop
    return windows

def selftest():
    assert T(0)==127 and T(500)==64 and T(1000)==0 and T(-500)==190
    assert source_derived(500,-250)==95 and source_derived(500,250)==33
    cases=[{"program":p,"base_instrument_sustain":b,
            "sustain_mod_env_permille":s,"preset_sustain_delta":s-b,
            "sample_id":43,"note":59,"velocity":100,"hold_mod_env_tc":0}
           for p,b,s in CASES]
    m={"schema":SCHEMA,"public_original_source_git_blob":SOURCE_GIT_BLOB,
       "original_six_presets_preserved":True,"original_25_instruments_preserved":True,
       "original_44_sample_records_preserved":True,"original_audio_pcm_byte_identical":True,
       "original_media_published":False,"instrument_bases":list(BASES),
       "requested_sustain_values":list(TARGETS),"cases":cases}
    g={"hardware":"sbawe64_gold","sample_ram_kib":28672,"p84_universal_sf2_test":True,
       "p75_private_sample_upload_plausible":True,
       "p75_private_sample_upload_write_words":100,
       "p75_private_sample_upload_minimum_words":25,
       "p64_original_win95_midi":{"p214_real_win95_driver_sweep":True,
         "p74_uart_frames_injected":112,
         "p214_original_creative_register_windows":[
           {"program":p,"start_row":i*100,"end_row":i*100+50,"window_isolated":True,
            "note":59,"velocity":100} for i,p in enumerate(PROGRAMS)]}}
    v={"agent_launched_in_actual_win95":True,
       "original_creative_winmm_endpoint_selected":True,"original_creative_com1_ready":True,
       "creatives_midi_short_messages_delivered":112,
       "audio_observed":True,"p84_universal_sf2_test":True,"win95_agent_error":False}
    assert len(validate_sources(m,g,v))==28
    mutations=(
       lambda a,b,c:a["cases"][9].update({"preset_sustain_delta":0}),
       lambda a,b,c:a["cases"][15].update({"base_instrument_sustain":1000}),
       lambda a,b,c:a.update({"original_audio_pcm_byte_identical":False}),
       lambda a,b,c:b["p64_original_win95_midi"].update({"p214_real_win95_driver_sweep":False}),
       lambda a,b,c:b["p64_original_win95_midi"]["p214_original_creative_register_windows"][13].update({"start_row":0}),
       lambda a,b,c:c.update({"original_creative_winmm_endpoint_selected":False}),
       lambda a,b,c:c.update({"creatives_midi_short_messages_delivered":111}),
       lambda a,b,c:b.update({"p75_private_sample_upload_plausible":False}),
       lambda a,b,c:a["cases"].pop(),
    )
    for f in mutations:
        a,b,c=deepcopy((m,g,v))
        f(a,b,c)
        try:validate_sources(a,b,c)
        except ValueError:pass
        else:raise AssertionError("P214 deliberately damaged evidence passed")
    print("P214 comparator selftest PASS: instrument/preset signed arithmetic and 9 rejected source/window mutations")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    for arg in ("manifest","guest_report","guest_verification","creative_csv",
                "derived_sf2","out"):
        p.add_argument("--"+arg.replace("_","-"),dest=arg,type=Path)
    a=p.parse_args()
    selftest()
    if a.self_test and not a.manifest:return
    require(all(getattr(a,n) for n in
          ("manifest","guest_report","guest_verification","creative_csv","derived_sf2","out")),
          "actual Creative source evidence required")
    manifest=json.loads(a.manifest.read_text())
    guest=json.loads(a.guest_report.read_text())
    verification=json.loads(a.guest_verification.read_text())
    windows=validate_sources(manifest,guest,verification)
    require(hashlib.sha256(a.derived_sf2.read_bytes()).hexdigest()==manifest.get("sf2_sha256"),
            "original Win95-loaded source bank does not match verified generated manifest")
    cases=[]
    ref_envval=None
    ref_pefe=None
    for settings,window in zip(manifest["cases"],windows):
        regs=original_csv(a.creative_csv,window["start_row"],window["end_row"])
        require(len({voice for voice,_,_ in regs})==1,
                "voice stealing or note overlap contaminated original Creative trace")
        hold=word(regs,"ATKHLD")
        sustain=word(regs,"DCYSUS")
        envval=word(regs,"ENVVAL")
        pefe=word(regs,"PEFE")
        require(len(hold)==1 and len(sustain)==2 and envval and pefe,
                "missing exact original Win95 modulation envelope registers")
        if ref_envval is None:
            ref_envval=envval
            ref_pefe=pefe
        require(envval==ref_envval and pefe==ref_pefe,
                "other original Creative voice generator paths differ unexpectedly")
        observed=sustain[0]>>8
        require(0<=observed<=127,"original driver sustain register high byte out of range")
        base=settings["base_instrument_sustain"]
        target=settings["sustain_mod_env_permille"]
        delta=settings["preset_sustain_delta"]
        if base==500:
            require(observed==REPEATED_BASE500[target],
                    "new original driver source-base500 controls disagree with genuine P210/P212")
        prediction=source_derived(base,delta)
        direct=T(target)
        cases.append({
           "program":settings["program"],"source_instrument_sustain":base,
           "preset_sustain_delta":delta,"requested_total_sustain":target,
           "original_Creative_SBAWE_DCYSUS_registers":[f"0x{x:04X}" for x in sustain],
           "observed_register_high_byte":observed,
           "source_derived_two_stage_prediction":prediction,
           "one_stage_direct_prediction":direct,
           "source_derived_two_stage_exact":observed==prediction,
           "one_stage_direct_exact":observed==direct,
           "previously_unseen_instrument_base":base!=500,
        })
    require(len(cases)==28 and len({(x["source_instrument_sustain"],x["requested_total_sustain"]) for x in cases})==28,
            "case variety or count lost")
    matched=sum(c["source_derived_two_stage_exact"] for c in cases)
    controls=sum(c["source_derived_two_stage_exact"] for c in cases if not c["previously_unseen_instrument_base"])
    new_matched=sum(c["source_derived_two_stage_exact"] for c in cases if c["previously_unseen_instrument_base"])
    out={
       "schema":"P214-genuine-original-Win95-Creative-independent-instrument-base-Sustain-v1",
       "source_run":"actual original Creative Windows95 guest experiment, 86Box AWE64 Gold",
       "reference_creative_vxd_sha256":ORIGINAL_VXD_SHA256,
       "original_public_sf2_git_blob":SOURCE_GIT_BLOB,
       "derived_sf2_sha256":manifest["sf2_sha256"],
       "source_original_six_presets_25_instruments_44_samples_preserved":True,
       "actual_original_driver_register_cases":cases,
       "new_non500_instrument_base_cases":21,
       "source_derived_two_stage_model_matches_all":matched,
       "source_derived_two_stage_model_matches_unseen_base_cases":new_matched,
       "source_derived_two_stage_model_matches_repeated_base500_cases":controls,
       "source_derived_generalization_supported_by_this_matrix":matched==28,
       "candidate_failure_is_research_evidence_not_CI_error":True,
       "new_original_Creative_run_executed":True,
       "full_VXD_generator_29_call_path_traced":False,
       "physical_Creative_EMU8000_test":"NOT RUN",
       "product_VST3_modified":False,
       "DAW_ASIO_test":"NOT RUN",
       "release":"NO-GO",
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=2)+"\n")
    print("P214 original Creative x instrument/preset Sustain: two-stage",
          matched,"/28; unseen instrument bases",new_matched,"/21; control base500",controls,"/7")
    if matched!=28:print("P214 FALSIFIED GENERALIZATION; retain genuine original driver observations; no DSP change")
    else:print("P214 source-derived layer conversion supported for tested bases; not full call-graph/physical parity")
if __name__=="__main__":main()
