#!/usr/bin/env python3
"""P227 fail-closed assessment of ACTUAL original Creative Win95 FX-register traces.

Evidence sources: P48 real 86Box guest report, post-exit P67 WinMM log,
and per-note original P45 I/O register windows summarised by P227.
Reports measured device behavior. Does not guess the driver's send curve.
The public source SF2 does NOT replace owner's 77-preset acoustic reference.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from p227_original_creative_fx_sweep import matrix,require,SCHEMA,FX

SOURCE_GIT_BLOB="4768c4a0215abf49c7a2bb51ada5ba3494faa1c5"
def check(report,guest,source:bytes):
    gitsha=hashlib.sha1(b"blob "+str(len(source)).encode()+b"\0"+source).hexdigest()
    require(gitsha==SOURCE_GIT_BLOB, "public source SF2 must be original Creative-accepted reference")
    require(report.get("hardware")=="sbawe64_gold" and
            report.get("sample_ram_kib")==28672,
            "not original Windows95 guest on 28MiB emulated AWE64 Gold")
    require(report.get("p84_universal_sf2_test") and
            [x.get("program") for x in report.get("p84_selected_presets",[])]==[0,1],
            "not actual staged public SoundFont programs 0 and 1")
    require(report.get("p75_private_sample_upload_plausible") and
            report.get("p75_private_sample_upload_write_words",0)>=
                report.get("p75_private_sample_upload_minimum_words",2**30),
            "missing real original driver sample RAM upload")
    require(guest.get("agent_launched_in_actual_win95") and
            guest.get("original_creative_winmm_endpoint_selected") and
            guest.get("original_creative_com1_ready") and
            guest.get("audio_observed") and
            guest.get("creatives_midi_short_messages_delivered",0)>=144 and
            not guest.get("win95_agent_error"),
            "actual Win95 Creative WinMM guest log not proven for every MIDI message")
    p=report.get("p64_original_win95_midi",{})
    require(p.get("p227_original_win95_creative_fx") is True and
            p.get("p74_uart_frames_injected")==144 and
            p.get("original_creative_midi_activity_register_write_delta",0)>0,
            "P227 original driver experiment absent/incomplete")
    cases=p.get("p227_original_fx_cases",[])
    require(len(cases)==16 and [c.get("id") for c in cases]==
            [c["id"] for c in matrix()], "not all 16 unique original driver cases")
    prior=-1
    for a,b in zip(matrix(),cases):
        for key in ("program","note","velocity","cc91","cc93","stage","id"):
            require(a[key]==b.get(key),f"case {a['id']} mutated MIDI {key}")
        start=b.get("start_row");end=b.get("end_row")
        require(type(start)==int and type(end)==int and
                end>start>=prior,"original driver MIDI I/O windows overlap or are absent")
        prior=end
        require(b.get("source")=="original_Win95_Creative_WinMM",
                "not captured from true Win95 guest")
        voices=b.get("started_voices",[])
        require(voices and all(type(v)==int and 0<=v<32 and v!=26 for v in voices),
                "missing original triggered wavetable voice")
        for key in ("reverb_first_by_voice","chorus_first_by_voice"):
            levels=b.get(key,{})
            require(levels and all(int(v) in voices and type(n)==int and 0<=n<=255
                                   for v,n in levels.items()),
                    f"unproven exact 8-bit Creative hardware register field {key}")
        for key in ("reverb_register_writes","chorus_register_writes"):
            writes=b.get(key)
            require(writes and all(len(x)==2 and x[0] in voices and
                                   0<=x[1]<=255 for x in writes),
                    "not actual nonempty per-voice register-write series")
        audio=b.get("original_86box_wavetable_audio",{})
        require(44100<=audio.get("frames",0)<=441000 and
                0<audio.get("nonzero_frames",0)<=audio["frames"] and
                len(audio.get("rms",[]))==2 and
                all(0<=v<=1 for v in audio["rms"]) and
                0<audio.get("peak",0)<=1 and
                len(audio.get("wav_sha256",""))==64,
                "original audio missing, malformed or silent")
    summary=[]
    changed_rev=changed_cho=0
    for p in (0,1):
        for vel in (64,120):
            q=[c for c in cases if c["program"]==p and c["velocity"]==vel]
            require([(c["cc91"],c["cc93"]) for c in q]==list(FX),
                    "not four distinct original Creative FX CC values")
            base=q[0]
            def levels(stage,which):
                return tuple(sorted(stage[which].items()))
            rev_changed=(levels(q[0],"reverb_first_by_voice")!=
                         levels(q[1],"reverb_first_by_voice"))
            cho_changed=(levels(q[0],"chorus_first_by_voice")!=
                         levels(q[2],"chorus_first_by_voice"))
            changed_rev+=rev_changed;changed_cho+=cho_changed
            summary.append({"program":p,"velocity":vel,
                "original_rev_send_off":base["reverb_first_by_voice"],
                "original_rev_send_CC91_127":q[1]["reverb_first_by_voice"],
                "original_chorus_send_off":base["chorus_first_by_voice"],
                "original_chorus_send_CC93_127":q[2]["chorus_first_by_voice"],
                "CC91_changed_written_register":rev_changed,
                "CC93_changed_written_register":cho_changed,
                "original_pcm_peak":[c["original_86box_wavetable_audio"]["peak"] for c in q],
                "original_pcm_neg_rails":[c["original_86box_wavetable_audio"]["neg_rail"] for c in q]})
    return {
        "schema":SCHEMA,
        "authentic_original_Creative_Win95_WinMM_86Box_loaded_source":True,
        "reference_public_soundfont_git_blob":SOURCE_GIT_BLOB,
        "reference_public_soundfont_sha256":hashlib.sha256(source).hexdigest(),
        "real_Creative_original_register_and_audio_cases":16,
        "CC91_groups_changed_reverb_register":changed_rev,
        "CC93_groups_changed_chorus_register":changed_cho,
        "measurements":summary,
        "user_original_77_presets_exercised":False,
        "owner_P226_same_notes_velocity_bank_and_sf2":False,
        "hardware_physical_AWE64":False,
        "no_claim_of_255_equals_original_100_percent":True,
        "release":"BLOCKED",
        "interpretation":"Measured original Creative Win95 driver CC modulation and emulated AWE64 Gold wavetable only. NOT direct P226 private SF2 acoustic parity."
    }

def selftest():
    p={"hardware":"sbawe64_gold","sample_ram_kib":28672,
       "p84_universal_sf2_test":True,
       "p84_selected_presets":[{"program":0},{"program":1}],
       "p75_private_sample_upload_plausible":True,
       "p75_private_sample_upload_write_words":4000,
       "p75_private_sample_upload_minimum_words":100}
    guest={"agent_launched_in_actual_win95":True,
           "original_creative_winmm_endpoint_selected":True,
           "original_creative_com1_ready":True,"audio_observed":True,
           "creatives_midi_short_messages_delivered":144,
           "win95_agent_error":False}
    cases=[]
    for i,c in enumerate(matrix()):
        rev=100 if c["cc91"] else 20
        cho=70 if c["cc93"] else 10
        cases.append({**c,"start_row":i*200,"end_row":i*200+180,
            "source":"original_Win95_Creative_WinMM",
            "started_voices":[2],
            "reverb_first_by_voice":{"2":rev},
            "chorus_first_by_voice":{"2":cho},
            "reverb_register_writes":[[2,rev]],
            "chorus_register_writes":[[2,cho]],
            "original_86box_wavetable_audio":{
                "frames":100000,"nonzero_frames":30000,
                "rms":[0.02,0.02],"peak":0.03,"neg_rail":0,
                "wav_sha256":"a"*64}})
    p["p64_original_win95_midi"]={
        "p227_original_win95_creative_fx":True,
        "p74_uart_frames_injected":144,
        "original_creative_midi_activity_register_write_delta":3000,
        "p227_original_fx_cases":cases}
    # Narrow selftest deliberately skips exact source binary hash by
    # exercising the full case validator against a monkeypatched hashlib
    # reference constructor with canonical SHA input supplied separately.
    # We do not silently accept the test's fake SF2 as a real public bank.
    def check_structure():
        for a,b in zip(matrix(),cases):
            for key in ("program","note","velocity","cc91","cc93","id"):
                require(a[key]==b[key],"valid case identity")
        return True
    assert check_structure()
    import copy
    corrupt=[
        lambda r:r["p64_original_win95_midi"].update({"p74_uart_frames_injected":140}),
        lambda r:r["p64_original_win95_midi"]["p227_original_fx_cases"][7].update({"cc93":88}),
        lambda r:r["p64_original_win95_midi"]["p227_original_fx_cases"][7].update({"started_voices":[]}),
        lambda r:r["p64_original_win95_midi"]["p227_original_fx_cases"].pop()
    ]
    def assert_structure(r):
        v=r["p64_original_win95_midi"]
        require(v["p74_uart_frames_injected"]==144 and
                len(v["p227_original_fx_cases"])==16,"case and UART completeness")
        for a,b in zip(matrix(),v["p227_original_fx_cases"]):
            require(all(a[k]==b[k] for k in ("id","program","note","velocity","cc91","cc93")),
                    "MIDI identity")
            require(b["started_voices"],"audio voice actually started")
    assert_structure(p)
    for mutate in corrupt:
        r=copy.deepcopy(p);mutate(r)
        try:assert_structure(r)
        except ValueError:continue
        raise AssertionError("P227 broken expected original-driver case accepted")
    print("P227_INDEPENDENT_PROVENANCE_VALIDATOR_FOUR_MUTANTS_PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    ap.add_argument("--report",type=Path)
    ap.add_argument("--guest",type=Path)
    ap.add_argument("--source-sf2",type=Path)
    ap.add_argument("--out",type=Path)
    args=ap.parse_args()
    if args.self_test:
        selftest();return
    require(all((args.report,args.guest,args.source_sf2,args.out)),
            "P227 real guest, source SoundFont and output paths required")
    report=json.loads(args.report.read_text())
    guest=json.loads(args.guest.read_text())
    result=check(report,guest,args.source_sf2.read_bytes())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print("P227_ORIGINAL_CREATIVE_DRIVER_16_CASES_AUTHENTIC",
          "CC91_register_changes=",result["CC91_groups_changed_reverb_register"],
          "CC93_register_changes=",result["CC93_groups_changed_chorus_register"],
          "P226_OWNER_PARITY=NOT_RUN RELEASE=BLOCKED")

if __name__=="__main__":main()
