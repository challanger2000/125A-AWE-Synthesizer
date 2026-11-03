"""P99 independent fidelity audit: reuse P97/P98, no GPL FSVR code imported.

Uses existing CT4390 analog reference metrics, retains original P97 global gain,
produces gain-independent spectral shape diagnostics and native PCM fingerprints.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import welch, find_peaks

MIN_RMS = 0.0005
MIN_STEREO_REFERENCE_DB = -30.0


def rd(n, places=3):
    return round(float(n), places)


def rms(samples):
    x = np.asarray(samples, dtype=np.float64)
    return float(np.sqrt(np.mean(x*x))) if x.size else 0.


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for part in iter(lambda: f.read(1024*1024), b""):
            h.update(part)
    return h.hexdigest()


def fingerprint(wav, sample_rate, note):
    # Stable body segment: compare the SAME MIDI and native sample timeline
    # across future engine builds, independent of capture clock phase.
    start = round((note["on_s"] + .35) * sample_rate)
    x = np.asarray(wav[start:start+sample_rate], dtype=np.float64)
    if len(x) != sample_rate or x.shape[1] != 2:
        raise ValueError("Unable to fingerprint MIDI onset {}".format(note["on_s"]))
    l, r = x[:, 0], x[:, 1]
    mid, side = (l+r)*.5, (l-r)*.5
    hz, power = welch(mid, sample_rate, nperseg=8192, noverlap=4096)
    audible = hz >= 30
    total_power = float(power[audible].sum())
    centroid = float((hz[audible]*power[audible]).sum()/total_power) if total_power else 0.
    peaks, _ = find_peaks(power)
    peaks = sorted((int(i) for i in peaks if hz[i]>=30),
                   key=lambda i: power[i], reverse=True)[:6]
    max_power = max(float(power.max()), 1e-30)
    block = round(sample_rate*.01)
    count = len(x)//block
    env = np.sqrt(np.mean((x[:count*block].reshape(count,block,2)/32768.)**2, axis=(1,2)))
    return {
        "rms_pcm16": rd(rms(x)),
        "peak_pcm16": int(np.max(np.abs(x))),
        "left_rms_pcm16": rd(rms(l)),
        "right_rms_pcm16": rd(rms(r)),
        "side_over_mid_db": rd(20*np.log10(max(rms(side), 1e-12)/max(rms(mid), 1e-12))),
        "spectral_centroid_hz": rd(centroid, 2),
        "top_spectral_peaks": [{"hz": rd(hz[i],1),
                "relative_db": rd(10*np.log10(max(float(power[i]),1e-30)/max_power),1)}
                              for i in peaks],
        "ten_ms_envelope_percentiles_dbfs":
            [rd(20*np.log10(max(float(v),1e-9)),2) for v in np.percentile(env,[10,50,90])],
    }


def score_group(group):
    notes=group["notes"]
    if len(notes)!=4:
        raise ValueError("P98 expected 4 notes for each effect A/B/C group")
    dry=float(notes[0]["metrics"]["body"]["native_minus_hardware_rms_db"])
    out=[]
    for step,note in enumerate(notes):
        m=note["metrics"]["body"]
        h_rms=float(m["hardware_rms"])
        e_rms=float(m["native_rms_global_gain_matched"])
        active=min(h_rms,e_rms)>MIN_RMS
        level=float(m["native_minus_hardware_rms_db"])
        h_side=float(m["hardware_side_to_mid_db"])
        e_side=float(m["native_side_to_mid_db"])
        # A dry/mono hardware reference's tiny side level mostly reports ADC
        # noise. Reject uninformative side/mid ratios rather than rank them.
        stereo=active and h_side>MIN_STEREO_REFERENCE_DB
        bands=[float(b["native_minus_hardware_db"])
               for b in note["metrics"]["body_spectral_bands"]
               if not b["reference_energy_weak"]]
        offset=float(np.median(bands)) if len(bands)>=3 else None
        # Timbral residual: median spectral offset REMOVED FROM SCORE ONLY.
        # The audio itself retains the single original P97 global gain.
        shape=float(np.sqrt(np.mean((np.asarray(bands)-offset)**2))) if offset is not None else None
        out.append({
            "step":step,"note":note["note"],"on_s":note["on_s"],
            "controller":note["controller"],"controller_value":note["controller_value"],
            "active_reference":active,
            "level_error_db":level if active else None,
            "level_error_relative_to_zero_send_db":rd(level-dry) if active else None,
            "spectral_shape_rms_db":rd(shape) if shape is not None else None,
            "median_band_difference_db":rd(offset) if offset is not None else None,
            "bands_used":len(bands),
            "stereo_hardware_side_to_mid_db":h_side if stereo else None,
            "stereo_native_side_to_mid_db":e_side if stereo else None,
            "stereo_width_error_db":rd(e_side-h_side) if stereo else None,
        })
    return out


def main():
    ap=argparse.ArgumentParser()
    for flag in ("p97","p98","native","midi","sf2","out","summary"):
        ap.add_argument("--"+flag, required=True)
    args=ap.parse_args()
    p97=json.loads(Path(args.p97).read_text(encoding="utf-8"))
    p98=json.loads(Path(args.p98).read_text(encoding="utf-8"))
    if p97.get("compared_seconds")!=264 or len(p98.get("subtests",[]))!=6:
        raise ValueError("P99 requires a full 264s P97 and six MIDI-validated P98 groups")
    wav, rate=sf.read(args.native,dtype="int16",always_2d=True)
    if rate!=44100 or wav.shape!=(264*44100,2):
        raise ValueError("Incorrect native 264s 44.1kHz stereo PCM16 rendering")
    groups=[]
    fingerprints=[]
    for group in p98["subtests"]:
        group_scores=score_group(group)
        groups.append({"effect":group["effect"],"variant":group["variant"],
                       "notes":group_scores})
        for note in group["notes"]:
            fingerprints.append({
                "effect":group["effect"],"variant":group["variant"],
                "note":note["note"],"on_s":note["on_s"],
                "native_pcm":fingerprint(wav,rate,note),
            })
    result={
        "experiment":"P99 independently coded CT4390 audio fidelity audit",
        "source_commit":os.environ.get("GITHUB_SHA","local"),
        "source_sha256":{
            "original_test_midi":sha256(args.midi),
            "original_test_soundfont":sha256(args.sf2),
            "current_native_render_pcm_wav":sha256(args.native),
        },
        "native_render":{"sample_rate_hz":rate,"duration_s":264,
                         "format":"stereo signed 16-bit PCM"},
        "global_p97_gain_db":p97["hardware_to_native_global_gain_match_db"],
        "groups":groups,
        "native_pcm_regression_fingerprints":fingerprints,
        "rules":{
            "minimum_active_RMS":MIN_RMS,
            "minimum_hardware_stereo_side_over_mid_db":MIN_STEREO_REFERENCE_DB,
            "timbre":"six broad bands, residual after subtracting median band shift; audio NOT EQ'd",
            "relative_to_dry":"report-only subtraction of first-step level discrepancy",
            "fingerprints":"fixed native PCM note segments; NOT physical hardware parity",
        },
        "limitations":[
            "Existing physical reference is analog 48kHz RCA capture, not S/PDIF",
            "No start/end marker tones in historical recording, so no clock-drift model is claimed",
            "A/C groups vary original SF2 note; only B repeats the same note at all sends",
            "Prior effect tails may overlap each note; subtest note body is not an isolated impulse",
            "Fingerprints are informational until a reviewed cross-build baseline is selected",
            "No FSVR GPLv3 source code was copied into this tool",
            "Physical chip sound fidelity remains unproven",
        ]
    }
    Path(args.out).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    lines=["# P99 – EMU8000 hardware-vs-render audit","",
           "All differences are emulator minus original CT4390 hardware. "
           "Original P97 global gain retained.","",
           "| Effect/test | Max-send body level | Level change from 0%-send | "
           "Spectral shape error | Stereo width difference |",
           "|---|---:|---:|---:|---:|"]
    def fmt(n):
        return "n/a" if n is None else "{:+.2f} dB".format(n)
    for g in groups:
        n=g["notes"][3]
        lines.append("| {} / {} | {} | {} | {} | {} |".format(
            g["effect"],g["variant"],fmt(n["level_error_db"]),
            fmt(n["level_error_relative_to_zero_send_db"]),
            fmt(n["spectral_shape_rms_db"]),fmt(n["stereo_width_error_db"])))
    lines.extend(["","Only B has exactly the same note at all four send settings.",
                  "Spectral timbre score is gain-independent; it is not an EQ correction.",
                  "The original analog reference cannot be sample-clock-aligned using absent markers.",
                  "CI PASS means the measurements ran, **not** 1:1 hardware fidelity.",""])
    Path(args.summary).write_text("\n".join(lines),encoding="utf-8")
    print("P99 PASS: 24 render fingerprints; 6 verified original MIDI effect groups")
    for g in groups:
        n=g["notes"][3]
        print("P99 {} {} max-send: level {:+.3f} dB, vs 0% {:+.3f} dB, stereo {}".format(
            g["effect"],g["variant"],n["level_error_db"],
            n["level_error_relative_to_zero_send_db"],n["stereo_width_error_db"]))


if __name__=="__main__":
    main()
