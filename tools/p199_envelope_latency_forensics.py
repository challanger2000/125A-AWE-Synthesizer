#!/usr/bin/env python3
"""P199: audit whether apparent EG2/EG1 release mismatch is an audio-capture
latency artifact, not an incorrect EMU8000 release slope. No DSP edits.
The original SHA-pinned CT4390 Gold SoundFont/MIDI/analog FLAC and native
render are compared with the ONE P97 global gain. Only analysis windows shift.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from p98_effect_subtests import load_events

RATE = 48000
TESTS = (("EG2_amp", 58, 1.5, 6.5), ("EG1_mod_pitch", 59, 9.5, 14.5))


def rms(x):
    a = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(a * a))) if len(a) else 0.0


def db(a):
    return float(20 * np.log10(max(a, 1e-12)))


def curve(audio, start, end, size=.01):
    # 10ms RMS; use stereo average energy, not phase-sensitive mixing of
    # the strongly different hardware/native stereo capture.
    t = np.arange(start, end - size/2, size)
    values = []
    for x in t:
        a = int(round(x*RATE))
        b = int(round((x+size)*RATE))
        values.append(rms(audio[a:b]))
    return np.asarray(t), np.asarray(values)


def shifted_energy(audio, start, end, lag_ms, step=.01):
    # Absolute common timeline. Never shift the actual rendered source.
    dt = lag_ms / 1000.
    return curve(audio, start+dt, end+dt, step)[1]


def signed_db_error(hw, em, pre_hw, pre_em):
    # Relative to the same note's hardware/native PRE-release plateau,
    # so the P97 global gain remains unchanged and differences in spectral
    # pan or analog gain do not masquerade as an envelope-time mismatch.
    return 20*np.log10(np.maximum(em, 1e-12)/pre_em) - \
           20*np.log10(np.maximum(hw, 1e-12)/pre_hw)


def identify_sounding_layers(meta):
    prog = [p for p in meta if p["program"] == 0 and p["bank"] == 0]
    if len(prog) != 1:
        raise ValueError("P199 needs original SF2 program zero")
    matches = {}
    for midi in (58, 59):
        layers = []
        for inst in prog[0]["instruments"]:
            general = {}
            for zone in inst["zones"]:
                g=zone["generator"]
                if "sampleID" in g:
                    if "keyRange" in g and not g["keyRange"][0] <= midi <= g["keyRange"][1]:
                        continue
                    layers.append({"instrument":inst["name"],
                                   "sample_id":g["sampleID"],
                                   "key_range":g.get("keyRange"),
                                   "zone_generators":g})
                else:
                    general.update(g)
        matches[str(midi)] = layers
    if sorted(l["sample_id"] for l in matches["58"]) != [42,43]:
        raise ValueError("P199 original AWE64 EG2 test is NOT two-layer fixture expected")
    if len(matches["59"]) != 1:
        raise ValueError("P199 EG1 expected single-layer note 59")
    return matches


def main():
    p = argparse.ArgumentParser()
    for k in ("reference","native","events","p97-report","p102-report","p105-report","sf2-metadata","out"):
        p.add_argument("--"+k,required=True)
    a=p.parse_args()
    p97=json.loads(Path(a.p97_report).read_text())
    p102=json.loads(Path(a.p102_report).read_text())
    p105=json.loads(Path(a.p105_report).read_text())
    meta=json.loads(Path(a.sf2_metadata).read_text())
    layers=identify_sounding_layers(meta)
    if p97["compared_seconds"] != 264:
        raise ValueError("P199 requires complete original P97 reference")
    events=load_events(a.events)
    for label,note,on,off in TESTS:
        found_on=[v for v in events if v["type"]=="note_on" and v["ch"]==0
                  and v["note"]==note and v["v"]>0 and abs(v["t"]-on)<.005]
        found_off=[v for v in events if v["ch"]==0 and v["note"]==note
                   and abs(v["t"]-off)<.005 and (v["type"]=="note_off"
                       or v["type"]=="note_on" and v["v"]==0)]
        if len(found_on)!=1 or len(found_off)!=1:
            raise ValueError("Original reference MIDI events not verified for "+label)
    hw,hr=sf.read(a.reference,frames=17*RATE,dtype="float32",always_2d=True)
    em,er=sf.read(a.native,frames=17*44100,dtype="float32",always_2d=True)
    if (hr,er)!=(RATE,44100) or hw.shape[1]!=2 or em.shape[1]!=2:
        raise ValueError("Unexpected P199 native/analog capture format")
    em=resample_poly(em,160,147,axis=0)
    lag_frames=round(p97["original_hardware_relative_latency_ms"]*RATE/1000)
    if lag_frames>=0:
        hw=hw[lag_frames:]
    else:
        em=em[-lag_frames:]
    em*=10.**(p97["hardware_to_native_global_gain_match_db"]/20)
    phase={r["test"]:r for r in p102["results"]}
    releases={r["test"]:r for r in p105["release_tests"]}
    rows=[]
    aggregate=[]
    for label,note,on,off in TESTS:
        old=phase[label];rel=releases[label]
        sections={q["phase"]:q for q in old["phases"]}
        before=sections["sustain"]["level_difference_db"]
        release=sections["release"]["level_difference_db"]
        slope=rel["physical"]["slope_db_per_s"]
        if slope>=-30 or slope<=-180:
            raise ValueError("Reference decay slope implausible")
        bias=release-before
        apparent_delay=1000.0*bias/abs(slope)
        # Fixed sustained reference is 0.10..0.35s before NoteOff;
        # avoid note-off transition, filter/FX startup and boundaries.
        _,pre_h=curve(hw,off-.38,off-.12)
        _,pre_e=curve(em,off-.38,off-.12)
        plateau_h=float(np.median(pre_h));plateau_e=float(np.median(pre_e))
        if min(plateau_h,plateau_e)<0.01:
            raise ValueError("No pre-NoteOff plateau")
        t,rh=curve(hw,off+.055,off+.265)
        _,rn=curve(em,off+.055,off+.265)
        if len(rh)!=len(rn):
            raise ValueError("Release vector mismatch")
        candidates=[]
        for lag_ms in range(-45,46):
            en=shifted_energy(em,off+.055,off+.265,lag_ms)
            valid=(rh>0.00035)&(en>0.00035)
            if valid.sum()<6:
                continue
            err=signed_db_error(rh[valid],en[valid],plateau_h,plateau_e)
            score=float(np.median(np.abs(err)))
            candidates.append({"analysis_lag_ms":lag_ms,
                               "median_abs_normalized_release_db":score,
                               "median_signed_normalized_release_db":float(np.median(err)),
                               "used_bins":int(valid.sum())})
        if not candidates:
            raise ValueError("P199 cannot estimate release alignment")
        optimal=min(candidates,key=lambda x:x["median_abs_normalized_release_db"])
        nominal=next(x for x in candidates if x["analysis_lag_ms"]==0)
        rows.append({
            "test":label,"note":note,
            "fixture_layers":layers[str(note)],
            "p102_sustain_level_db":before,
            "p102_release_level_db":release,
            "release_minus_sustain_db":round(bias,3),
            "physical_release_slope_db_s":slope,
            "native_release_slope_db_s":rel["native"]["slope_db_per_s"],
            "apparent_delay_from_p102_db_ms":round(apparent_delay,2),
            "actual_release_analysis_zero_shift":nominal,
            "best_analysis_only_lag":optimal,
            "best_lag_not_applied_to_audio":True,
            "sample_clock_or_capture_delay_not_independently_calibrated":True
        })
        aggregate.append(optimal["analysis_lag_ms"])
        print("P199 %-15s release-vs-sustain apparent delay %+.2fms; "
              "10ms RMS analysis best lag %+dms (median abs error %.2f -> %.2f dB), "
              "hardware slope %.2f vs native %.2f dB/s" %
              (label,apparent_delay,optimal["analysis_lag_ms"],
               nominal["median_abs_normalized_release_db"],
               optimal["median_abs_normalized_release_db"],slope,rel["native"]["slope_db_per_s"]))
    # Attack is evaluated separately, after note 58's early secondary layer.
    # Its output is a TWO-VOICE MIX, not a single hardware EG2 envelope.
    start=2.52;end=3.45
    _,attack_hw=curve(hw,start,end);_,attack_em=curve(em,start,end)
    _,hold_hw=curve(hw,3.75,4.15);_,hold_em=curve(em,3.75,4.15)
    hpeak=float(np.median(hold_hw));epeak=float(np.median(hold_em))
    if min(hpeak,epeak)<.03:
        raise ValueError("P199 invalid note58 hold reference")
    mask=(attack_hw/hpeak > .025)&(attack_em/epeak >.025)
    early_err=signed_db_error(attack_hw[mask],attack_em[mask],hpeak,epeak)
    attack={
        "original_fixture_hardware_voices":2,
        "comparison_window_s":[start,end],
        "relative_to_each_capture_hold_median":True,
        "active_bins":int(mask.sum()),
        "median_signed_native_minus_hardware_attack_shape_db":
            round(float(np.median(early_err)),3) if len(early_err) else None,
        "median_abs_attack_shape_error_db":
            round(float(np.median(np.abs(early_err))),3) if len(early_err) else None,
        "phase_2_amplitude_median_differences_from_p102":
            {p:next(x for x in phase["EG2_amp"]["phases"] if x["phase"]==p)["level_difference_db"]
             for p in ("attack","hold","decay","sustain")},
        "caveat":"Second simultaneous note58 sampleID42 (+24 semitones, fast-decay layer) means composite attack is not direct isolated chip EG2 shape."
    }
    print("P199 EG2 attack relative to hold: median signed %.3fdB / median abs %.3fdB; %d active 10ms windows; TWO original layers" %
          (attack["median_signed_native_minus_hardware_attack_shape_db"],
           attack["median_abs_attack_shape_error_db"],attack["active_bins"]))
    out={"experiment":"P199 AWE64 Gold real-capture relative envelope timing audit",
         "reference":"Original pinned analog CT4390 FLAC and MIDI, not S/PDIF",
         "single_original_global_p97_gain_db":p97["hardware_to_native_global_gain_match_db"],
         "P97_original_50ms_alignment_ms":p97["original_hardware_relative_latency_ms"],
         "release":rows,"eg2_attack":attack,
         "summary": "P102 release level bias cannot be interpreted as DSP error without finer temporal alignment; compare independent per-note lags and slopes.",
         "limitations":[
             "Best lag is diagnostic only; no audio resampling or playback change.",
             "Analog hardware capture and MIDI/software clocks differ; lag may also include filter/FX and dynamic envelope changes.",
             "Original note58 includes two distinct sounding SF2 instrument zones; composite spectrum is not direct isolated volume envelope.",
             "EG1 mod-to-pitch test has a single zone, but amplitude release measures the volume envelope, not EG1 pitch trajectory.",
             "No physical chip register/digital recording proof of a silicon-accurate individual EG shape.",
             "Do not apply a time shift in production based on this analysis."] }
    Path(a.out).write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
