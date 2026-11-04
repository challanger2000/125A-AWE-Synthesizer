"""P102 – measured six-stage EMU8000 amp/mod envelope, real CT4390 comparison.

Reuses SHA-verified SoundFont Spec Test v3.0, MIDI-derived timing and P97 global
level matching. No new DSP theory, no per-note audio level fitting. The second
test is modulation-envelope-to-PITCH, not a direct filter-envelope recording.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from p98_effect_subtests import load_events

RATE = 48000
PHASES = ("delay", "attack", "hold", "decay", "sustain", "release")
# This original test consists of a short announcement click then a 5 s tone;
# the note-off is at the start of release. Each SF2 stage is 1 s long.
TESTS = (
    {"label": "EG2_amp", "note": 58, "on": 1.5, "off": 6.5},
    {"label": "EG1_mod_pitch", "note": 59, "on": 9.5, "off": 14.5},
)


def rms(x):
    a = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(a * a))) if a.size else 0.0


def ratio_db(a, b):
    return float(20 * np.log10(max(float(a), 1e-10) / max(float(b), 1e-10)))


def verify_midi(events):
    for t in TESTS:
        ons = [e for e in events if e["type"] == "note_on"
               and e["ch"] == 0 and e["note"] == t["note"]
               and e["v"] > 0 and abs(e["t"]-t["on"]) < .005]
        offs = [e for e in events if e["ch"] == 0 and e["note"] == t["note"]
                and abs(e["t"]-t["off"]) < .005
                and (e["type"] == "note_off"
                     or (e["type"] == "note_on" and e["v"] == 0))]
        if len(ons) != 1 or len(offs) != 1:
            raise ValueError("Original MIDI onset/note-off mismatch: {}".format(t))
        if sum(1 for e in events if e["type"] == "note_on" and e["ch"] == 0
               and e["note"] == t["note"] and e["v"] > 0
               and t["on"]-.01 <= e["t"] <= t["off"]+.01) != 1:
            raise ValueError("Ambiguous MIDI note activity")
    print("P102 verified original MIDI: 1.50-6.50s amp, 9.50-14.50s modulation")


def get_envelope(audio, seconds, end_s, step=.02):
    points = np.arange(seconds, end_s, step)
    result = []
    for t in points:
        a = int(round(t * RATE))
        b = int(round((t + step) * RATE))
        result.append(rms(audio[a:b, :]))
    return points, np.asarray(result)


def pitch_peak(audio, t, length=.18):
    """Dominant short-time harmonic; a diagnostic, not guaranteed fundamental."""
    a, b = int((t - length/2) * RATE), int((t + length/2) * RATE)
    if a < 0 or b > len(audio) or b-a < 4096:
        return None
    x = np.mean(audio[a:b], axis=1, dtype=np.float64)
    if rms(x) < 0.0005:
        return None
    x = x - x.mean()
    w = np.hanning(len(x))
    spec = np.abs(np.fft.rfft(x*w, n=65536))
    freq = np.fft.rfftfreq(65536, 1/RATE)
    valid = (freq>=55)&(freq<=4000)
    if not np.any(valid):
        return None
    i = int(np.argmax(spec*valid))
    if i<1 or i>=len(spec)-1:
        return None
    # Parabolic interpolation of log amplitude (log-spectral-peak estimate).
    lo,mid,hi = np.log(np.maximum(spec[i-1:i+2],1e-15))
    denom = lo - 2*mid + hi
    off = .5*(lo-hi)/denom if abs(denom)>1e-8 else 0
    return float((i+np.clip(off,-.5,.5))*RATE/65536)


def main():
    p=argparse.ArgumentParser()
    for x in ("reference","native","events","p97-report","out"):
        p.add_argument("--"+x,required=True)
    a=p.parse_args()
    report97=json.loads(Path(a.p97_report).read_text(encoding="utf-8"))
    if report97.get("compared_seconds")!=264:
        raise ValueError("P102 needs complete P97 264-second hardware comparison")
    verify_midi(load_events(a.events))

    # Only the first 16s is needed; historical original test provides no
    # clock fiducials, so DO NOT claim sample-accurate phase alignment.
    hw,hr=sf.read(a.reference,frames=RATE*17,dtype="float32",always_2d=True)
    emu,er=sf.read(a.native,frames=44100*17,dtype="float32",always_2d=True)
    if (hr,er)!=(48000,44100) or hw.shape[1]!=2 or emu.shape[1]!=2:
        raise ValueError("P102 recording format mismatch")
    emu=resample_poly(emu,160,147,axis=0)
    lag=round(report97["original_hardware_relative_latency_ms"]*RATE/1000.)
    if lag>=0:
        hw=hw[lag:]
    else:
        emu=emu[-lag:]
    if min(len(hw),len(emu)) < 16*RATE:
        raise ValueError("P102 available aligned recording shorter than 16s")
    gain_db=report97["hardware_to_native_global_gain_match_db"]
    emu=emu * (10**(gain_db/20))
    all_results=[]
    for test in TESTS:
        phase_data=[]
        curves_h=[]
        curves_e=[]
        for i,phase in enumerate(PHASES):
            t0=test["on"]+i
            # Exclude 50ms transitions; the original 'click' overlaps
            # the first 0.5s of the delayed sound. Use only 0.55..0.90s.
            start=.55 if i==0 else .10
            end=.90 if i==0 else .90
            ticks, rh=get_envelope(hw,t0+start,t0+end)
            _, re=get_envelope(emu,t0+start,t0+end)
            curves_h.extend(rh.tolist() if i>=1 else [])
            curves_e.extend(re.tolist() if i>=1 else [])
            active=(rh>0.0005)&(re>0.0005)
            level=float(np.median(20*np.log10(re[active]/rh[active]))) if np.any(active) else None
            row={"phase":phase,"window_s":[round(t0+start,3),round(t0+end,3)],
                 "hardware_rms":round(float(np.median(rh)),7),
                 "emulated_rms_matched":round(float(np.median(re)),7),
                 "level_difference_db":round(level,3) if level is not None else None,
                 "active_20ms_bins":int(active.sum())}
            if test["label"]=="EG1_mod_pitch" and i>=1:
                centers=np.arange(t0+.18,t0+.90,.12)
                pitches=[]
                for t in centers:
                    h=pitch_peak(hw,t)
                    e=pitch_peak(emu,t)
                    if h and e:
                        cents=1200*np.log2(e/h)
                        pitches.append({"t":round(float(t),3),"hardware_hz":round(h,3),
                                        "emulated_hz":round(e,3),
                                        "dominant_peak_difference_cents":round(float(cents),2)})
                row["dominant_peak_samples"]=pitches
                if pitches:
                    row["dominant_peak_median_difference_cents"]=round(
                        float(np.median([x["dominant_peak_difference_cents"]
                                         for x in pitches])),2)
            phase_data.append(row)
        ch=np.asarray(curves_h);ce=np.asarray(curves_e)
        valid=(ch>0.0005)&(ce>0.0005)
        if int(valid.sum())<30:
            raise ValueError("Insufficient active audio for "+test["label"])
        env_log_corr=float(np.corrcoef(np.log10(ch[valid]),np.log10(ce[valid]))[0,1])
        # Relative curve shape, after subtracting one median offset in dB
        # from comparison of the metrics only. No audio modifications.
        diff=20*np.log10(ce[valid]/ch[valid])
        shape_error=float(np.sqrt(np.mean((diff-np.median(diff))**2)))
        item={"test":test["label"],"midi_note":test["note"],
              "midi_on_s":test["on"],"midi_off_s":test["off"],
              "envelope_curve_log_correlation":round(env_log_corr,5),
              "envelope_shape_error_db_after_offset":round(shape_error,3),
              "phases":phase_data}
        all_results.append(item)
    out={"experiment":"P102 six-phase original CT4390 envelope comparison",
         "hardware":"AWE64 Gold CT4390 analog line-out, v3.0 genuine reference",
         "render":"current native 86Box-derived EMU8000 at 44100Hz, shared original SF2",
         "single_global_p97_gain_db":gain_db,
         "p97_lag_ms":report97["original_hardware_relative_latency_ms"],
         "results":all_results,
         "limitations":[
             "Test 1 measures amplitude stages, test 2 mod-envelope-to-PITCH; "
             "test 2 is not a direct measurement of mod-envelope-to-FILTER.",
             "Same EG1 generator drives filter modulation in the chip, "
             "but correct filter depth/curve must be validated separately.",
             "Short-time dominant spectral peak may be a harmonic rather than "
             "the fundamental: peak deltas are diagnostics, not certified pitch errors.",
             "AWE64 analog path, original driver setup and P97 global gain only. "
             "No per-note/phase gain or phase/time warping.",
             "Original MIDI includes an announcement click during the delay stages; "
             "the click-contaminated first half of delay is omitted.",
             "P97 coarse 50ms alignment may shift stage boundaries; bins "
             "near phase edges are excluded.",
         ]}
    Path(a.out).write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print("P102 original hardware envelope phases:")
    for test in all_results:
        print("P102 {} correlation {:.4f}, shape residual {:.2f} dB".format(
            test["test"], test["envelope_curve_log_correlation"],
            test["envelope_shape_error_db_after_offset"]))
        for phase in test["phases"]:
            print("P102 {} {:>7s}: level {} dB, active bins {}".format(
                test["test"],phase["phase"],phase["level_difference_db"],
                phase["active_20ms_bins"]))


if __name__=="__main__":
    main()
