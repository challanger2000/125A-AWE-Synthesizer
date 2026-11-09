#!/usr/bin/env python3
"""P197: separate SF2 attenuation register gain from overlap, onset and ADC
effects on original AWE64 CT4390 264s capture. A numerical diagnostic; never
modify or normalise each individual audio note.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from p98_effect_subtests import load_events

TEST_NOTES=(65,66,67,68,69)
TEST_TIMES=(86.5,87.0,87.5,88.0,88.5)
# Onset is followed by sustain. 420 ms MIDI duration, 80 ms before next note.
WINDOWS=(("onset", .02,.08),("early",.08,.16),
         ("middle",.16,.25),("late",.25,.34),
         ("pre_off",.34,.40),("post_off",.43,.48))
RATE=48000

def rms(x):
    a=np.asarray(x,dtype=np.float64)
    return float(np.sqrt(np.mean(a*a))) if a.size else 0.0

def db(x):
    return float(20*np.log10(max(float(x),1e-14)))

def main():
    ap=argparse.ArgumentParser()
    for k in ("reference","native","events","p97-report","sf2-metadata","out"):
        ap.add_argument("--"+k,required=True)
    a=ap.parse_args()
    p97=json.loads(Path(a.p97_report).read_text())
    meta=json.loads(Path(a.sf2_metadata).read_text())
    if p97["compared_seconds"]!=264:
        raise ValueError("Required complete P97 264s physical oracle")
    prog=[x for x in meta if x["bank"]==0 and x["program"]==0]
    if len(prog)!=1:
        raise ValueError("Original test SoundFont program zero not present")
    target={}
    for inst in prog[0]["instruments"]:
        if inst["name"]!="instrumentAtten":
            continue
        for zone in inst["zones"]:
            gen=zone["generator"]; key=gen.get("keyRange")
            if key and key[0]==key[1] and key[0] in TEST_NOTES:
                target[key[0]]=gen
    for note in TEST_NOTES:
        g=target.get(note)
        if g is None or g.get("sampleID")!=43 or g.get("overridingRootKey")!=note or g.get("initialAttenuation")!=(note-63)*50:
            raise ValueError("P197 real SF2 five-note same-sample/same-pitch control NOT MET: %s: %s"%(note,g))
    events=load_events(a.events)
    for note,t in zip(TEST_NOTES,TEST_TIMES):
        ons=[e for e in events if e["type"]=="note_on" and e["ch"]==0
             and e["note"]==note and e["v"]==127 and abs(e["t"]-t)<.005]
        offs=[e for e in events if e["type"] in ("note_off","note_on") and e["ch"]==0
              and e["note"]==note and e["t"]>t and e["t"]<t+.48
              and (e["type"]=="note_off" or e["v"]==0)]
        if len(ons)!=1 or len(offs)!=1 or abs(offs[0]["t"]-t-.42)>.03:
            raise ValueError("P197 MIDI timeline unexpected for note "+str(note))
    ref,rr=sf.read(a.reference,frames=90*RATE,dtype="float32",always_2d=True)
    native,nr=sf.read(a.native,frames=90*44100,dtype="float32",always_2d=True)
    if (rr,nr)!=(RATE,44100) or ref.shape[1]!=2 or native.shape[1]!=2:
        raise ValueError("P197 unsupported capture format")
    emu=resample_poly(native,160,147,axis=0)
    lag=round(p97["original_hardware_relative_latency_ms"]*RATE/1000.0)
    if lag>=0:
        ref=ref[lag:]
    else:
        emu=emu[-lag:]
    emu*=10.0**(p97["hardware_to_native_global_gain_match_db"]/20)
    report=[]
    for name,lo,hi in WINDOWS:
        levels=[]
        for note,t in zip(TEST_NOTES,TEST_TIMES):
            i=round((t+lo)*RATE);j=round((t+hi)*RATE)
            r=ref[i:j];e=emu[i:j]
            if len(r)!=len(e) or len(r)<1000:
                raise ValueError("Insufficient note phase samples")
            record={"note":note,"atten_cb":target[note]["initialAttenuation"],
                    "hardware_mid_rms":rms(r.mean(axis=1)),
                    "emulated_mid_rms":rms(e.mean(axis=1)),
                    "hardware_stereo_rms":rms(r),
                    "emulated_stereo_rms":rms(e),
                    "hardware_peak":float(np.max(np.abs(r))),
                    "emulated_peak":float(np.max(np.abs(e)))}
            levels.append(record)
        base=levels[0]
        for item in levels:
            item["hardware_relative_loss_db"]=round(db(base["hardware_mid_rms"]/max(item["hardware_mid_rms"],1e-14)),3)
            item["native_relative_loss_db"]=round(db(base["emulated_mid_rms"]/max(item["emulated_mid_rms"],1e-14)),3)
            item["relative_error_db"]=round(item["native_relative_loss_db"]-item["hardware_relative_loss_db"],3)
        hw_slope=(levels[-1]["hardware_relative_loss_db"]-levels[0]["hardware_relative_loss_db"])/4
        native_slope=(levels[-1]["native_relative_loss_db"]-levels[0]["native_relative_loss_db"])/4
        report.append({"phase":name,"onset_offset_s":[lo,hi],
                       "hardware_db_per_5db_sf2":round(hw_slope,3),
                       "native_db_per_5db_sf2":round(native_slope,3),
                       "native_minus_hardware_step_db":round(native_slope-hw_slope,3),
                       "samples":levels})
        print("P197 %-8s hardware %.3f vs native %.3f dB/5SF2dB; residual %+.3f dB/step"
              %(name,hw_slope,native_slope,native_slope-hw_slope))
        print("P197 %-8s error by note: %s"%
              (name, [(p["note"],p["relative_error_db"]) for p in levels]))
    output={"experiment":"P197 original AWE64 SF2 attenuation onset/body/off windows",
            "source":"SHA-pinned CT4390 analog and original SoundFont Test v3.0",
            "source_fixture_control":"same sampleID=43, same pitch by per-note overridingRootKey; 100..300 cB in 50 cB increments",
            "window_results":report,
            "limitations":["Original CT4390 capture analog; no hardware raw register snapshot.",
                           "Possible time-dependent effects, clip/nonlinear output, and previous note release/FX tails.",
                           "No individual per-note PCM normalization; one prior global 264s P97 gain only.",
                           "This is NOT direct proof of SF2 centibel-to-chip-register formula." ]}
    Path(a.out).write_text(json.dumps(output,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
