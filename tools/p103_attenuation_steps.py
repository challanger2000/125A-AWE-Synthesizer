"""P103 original AWE64 CT4390 SoundFont v3.0 attenuation-step audit.

Hardware test #11: SF2 generator initialAttenuation steps 0..30 dB
become ~0..12 dB on Sound Blaster (0.4 dB / SF2 dB). Verify both
hardware and our Win95-profile engine before touching the converter.

The MIDI announces the test on a separate simultaneous note until 86.5s.
Only unmasked notes #65..69, beginning at 86.5s, are usable for this
simple RMS ratio. Do NOT turn a hardware-output curve into a claim about
unseen guest VXD register arithmetic.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from p98_effect_subtests import load_events


def rms(a):
    return float(np.sqrt(np.mean(np.square(a, dtype=np.float64))))


def db(a, b):
    return float(20*np.log10(max(a, 1e-10)/max(b, 1e-10)))


def main():
    p=argparse.ArgumentParser()
    for key in ("reference","native","events","p97-report","out"):
        p.add_argument("--"+key,required=True)
    a=p.parse_args()
    events=load_events(a.events)
    # The first 2 notes (63/64) overlap the spoken test announcement;
    # start at the first clean post-announcement note (65, 86.5s).
    notes=(65,66,67,68,69)
    times=(86.5,87.0,87.5,88.0,88.5)
    starts=[]
    for note, t in zip(notes,times):
        hits=[e for e in events if e["type"]=="note_on"
              and e["ch"]==0 and e["note"]==note and e["v"]==127
              and abs(e["t"]-t)<.005]
        offs=[e for e in events if e["ch"]==0 and e["note"]==note
              and e["t"]>t and e["t"]<t+.6
              and (e["type"]=="note_off"
                   or (e["type"]=="note_on" and e["v"]==0))]
        if len(hits)!=1 or len(offs)!=1 or abs(offs[0]["t"]-t-.42)>.03:
            raise ValueError("Original SHA-pinned MIDI note/length invalid "+str(note))
        starts.append(t)

    report=json.loads(Path(a.p97_report).read_text())
    if report.get("compared_seconds")!=264:
        raise ValueError("P103 requires verified P97 full hardware comparison")
    ref, rr=sf.read(a.reference,frames=90*48000,always_2d=True,dtype="float32")
    out, nr=sf.read(a.native,frames=90*44100,always_2d=True,dtype="float32")
    if (rr,nr)!=(48000,44100):
        raise ValueError("Unexpected sample rate")
    out=resample_poly(out,160,147,axis=0)
    lag=round(report["original_hardware_relative_latency_ms"]*48)
    if lag>=0:
        ref=ref[lag:]
    else:
        out=out[-lag:]
    out*=10**(report["hardware_to_native_global_gain_match_db"]/20)
    measures=[]
    for note,t in zip(notes,starts):
        # All voices share same note-on velocity and a 420ms MIDI length.
        # 90..320ms excludes onset and avoids release/next-note tails.
        a0=round((t+.09)*rr)
        a1=round((t+.32)*rr)
        hw=rms(ref[a0:a1].mean(axis=1))
        em=rms(out[a0:a1].mean(axis=1))
        measures.append({"note":note,"on_s":t,
                         "hardware_mid_rms":round(hw,8),
                         "native_mid_rms":round(em,8)})
    if min(z["hardware_mid_rms"] for z in measures)<.00001:
        raise ValueError("Hardware quiet for attenuation fixture")
    first=measures[0]
    for i,entry in enumerate(measures):
        entry["relative_sf2_attenuation_db"]=10+i*5
        entry["hardware_loss_vs_10db_sf2"]=round(
            db(first["hardware_mid_rms"],entry["hardware_mid_rms"]),3)
        entry["native_loss_vs_10db_sf2"]=round(
            db(first["native_mid_rms"],entry["native_mid_rms"]),3)
    hw=(measures[-1]["hardware_loss_vs_10db_sf2"]
        -measures[0]["hardware_loss_vs_10db_sf2"])/4
    em=(measures[-1]["native_loss_vs_10db_sf2"]
        -measures[0]["native_loss_vs_10db_sf2"])/4
    result={"experiment":"P103 real AWE64 Gold SF2 initial attenuation test #11",
            "midi":"SHA-pinned original MIDI 65-69; test #11, notes after announcement",
            "source":"analog physical AWE64 Gold CT4390 vs own 86Box native",
            "level_matching":"same global P97 match, relative inter-note losses",
            "steps":measures,
            "physical_hardware_increment_db_per_5db_sf2":round(hw,3),
            "native_increment_db_per_5db_sf2":round(em,3),
            "native_minus_hardware_per_step_db":round(em-hw,3),
            "physical_expected_by_test_author_db_per_5db_sf2":2.0,
            "limitations":[
                "Analog hardware, no S/PDIF needed for relative gain comparison.",
                "Sample pitches differ between MIDI notes 65-69. Sample-tone "
                "content can bias broadband RMS; this test alone does not "
                "prove a specific Creative VXD conversion formula.",
                "Test #11 uses successive 5-dB SF2 increments and ignores "
                "first two notes which overlap the test announcement.",
                "P97 50ms alignment may shift note boundaries slightly, "
                "but central 90..320ms windows avoid both edges.",
            ]}
    Path(a.out).write_text(json.dumps(result,indent=2)+"\n")
    print("P103 real AWE64 attenuation: step hardware={:+.3f} dB / 5 SF2 dB; native={:+.3f} dB; delta={:+.3f} dB".format(hw,em,em-hw))
    for z in measures:
        print("P103 note {}: physical loss {:+.3f} dB; native loss {:+.3f} dB".format(
            z["note"],z["hardware_loss_vs_10db_sf2"],z["native_loss_vs_10db_sf2"]))


if __name__=="__main__":
    main()
