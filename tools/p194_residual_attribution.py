#!/usr/bin/env python3
"""P194: decompose the SAME CT4390-vs-125A spectral delta into absolute
energy contributions, not just ratios from nearly silent test sections.
Reproduces P97's exact global 1-second Hann FFT oracle as an independent
end-to-end check; does not modify PCM or production DSP.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


RATE = 48000
BANDS = [(50, 200), (200, 500), (500, 2000),
         (2000, 5000), (5000, 10000), (10000, 20000)]


def main():
    parser = argparse.ArgumentParser()
    for key in ("reference", "native", "p97-report", "p102-report", "out"):
        parser.add_argument("--" + key, required=True)
    a = parser.parse_args()
    p97 = json.loads(Path(a.p97_report).read_text(encoding="utf-8"))
    p102 = json.loads(Path(a.p102_report).read_text(encoding="utf-8"))
    if p97["compared_seconds"] != 264:
        raise ValueError("P194 requires the complete 264s CT4390 capture")
    ref, rr = sf.read(a.reference, dtype="float32", always_2d=True)
    native, nr = sf.read(a.native, dtype="float32", always_2d=True)
    if rr != RATE or nr != 44100 or ref.shape[1] != 2 or native.shape[1] != 2:
        raise ValueError("Wrong reference/native format; cannot attribute differences")

    emu = resample_poly(native, 160, 147, axis=0)
    bin_frames = 2400  # identical 50 ms alignment resolution as P97
    lag_bins = int(round(p97["original_hardware_relative_latency_ms"] / 50.0))
    if lag_bins >= 0:
        ref = ref[lag_bins * bin_frames:]
    else:
        emu = emu[-lag_bins * bin_frames:]
    max_frames = min(len(ref), len(emu), 264 * RATE - abs(lag_bins) * bin_frames)
    ref, emu = ref[:max_frames], emu[:max_frames]
    match_db = float(p97["hardware_to_native_global_gain_match_db"])

    hz = np.fft.rfftfreq(RATE, 1.0 / RATE)
    ix = [(hz >= lo) & (hz < hi) for lo, hi in BANDS]
    window = np.hanning(RATE)
    sections = p97["sections"]
    pools = [{"name": s["test"], "time_s": s["time_s"], "ref": np.zeros(len(BANDS)),
              "emu": np.zeros(len(BANDS)), "seconds": 0} for s in sections]
    global_ref = np.zeros(len(BANDS))
    global_emu = np.zeros(len(BANDS))
    every_second = []
    gain_power = 10.0 ** (match_db / 10.0)

    for i in range(max_frames // RATE):
        r = ref[i * RATE:(i + 1) * RATE]
        e = emu[i * RATE:(i + 1) * RATE]
        if np.sqrt(np.mean(r * r)) < .002:
            continue
        rpow = np.abs(np.fft.rfft(r.mean(axis=1) * window)) ** 2
        epow = np.abs(np.fft.rfft(e.mean(axis=1) * window)) ** 2
        rp = np.asarray([rpow[z].sum() for z in ix])
        ep = np.asarray([epow[z].sum() for z in ix]) * gain_power
        global_ref += rp
        global_emu += ep
        secid = next((j for j, s in enumerate(sections)
                      if s["time_s"][0] <= i + .5 < s["time_s"][1]), None)
        if secid is not None:
            pools[secid]["ref"] += rp
            pools[secid]["emu"] += ep
            pools[secid]["seconds"] += 1
        every_second.append((i, float(rp[0]), float(ep[0]), secid))

    if len(every_second) != p97["number_active_spectral_windows"]:
        raise ValueError("P97 active-window reproduction mismatch: %d != %d" %
                         (len(every_second), p97["number_active_spectral_windows"]))
    if np.any(global_ref <= 0):
        raise ValueError("Insufficient hardware energy")
    deltas = 10.0 * np.log10(np.maximum(global_emu, 1e-12) /
                              np.maximum(global_ref, 1e-12))
    for k, (lo, hi) in enumerate(BANDS):
        expected = next(x for x in p97["band_spectrum"]
                        if x["band_hz"] == "%d-%d" % (lo, hi))
        if abs(deltas[k] - expected["native_minus_real_db_level_matched"]) > .02:
            raise ValueError("P194/P97 spectrum mismatch in %d-%d Hz: %.3f vs %s" %
                             (lo, hi, deltas[k], expected))
    total_delta = float(global_emu[0] - global_ref[0])
    if total_delta <= 0:
        raise ValueError("Current P193 global 50-200 Hz excess not reproduced")

    ranked = []
    for q in pools:
        rp, ep = q["ref"][0], q["emu"][0]
        ranked.append({
            "test": q["name"], "time_s": q["time_s"],
            "active_seconds": q["seconds"],
            "hardware_50_200_power": float(rp),
            "native_matched_50_200_power": float(ep),
            "hardware_fraction_of_global_50_200_power": round(float(rp / global_ref[0]), 6),
            "native_minus_hardware_50_200_power": float(ep - rp),
            "contribution_to_global_excess_percent": round(float(100 * (ep - rp) / total_delta), 3),
            "local_50_200_error_db": round(float(10 * np.log10(
                max(ep, 1e-16) / max(rp, 1e-16))), 3) if rp else None,
        })
    ranked.sort(key=lambda x: x["native_minus_hardware_50_200_power"], reverse=True)
    top_seconds = sorted(every_second, key=lambda s: s[2] - s[1], reverse=True)[:16]
    details = []
    for s in top_seconds:
        n, rp, ep, secid = s
        details.append({"second_start": n,
                        "section": pools[secid]["name"] if secid is not None else None,
                        "reference_power": rp, "native_matched_power": ep,
                        "net_excess_percent": round(float(100 * (ep - rp) / total_delta), 3),
                        "ratio_db": round(float(10 * np.log10(
                            max(ep, 1e-16) / max(rp, 1e-16))), 3)})
    # The original P102 has 180ms dominant-peak estimates. Keep the exact
    # measured frequencies, not a fictional voice fundamental estimate.
    mod = next(r for r in p102["results"] if r["test"] == "EG1_mod_pitch")
    attack = next(p for p in mod["phases"] if p["phase"] == "attack")
    hold = next(p for p in mod["phases"] if p["phase"] == "hold")
    pitches = attack["dominant_peak_samples"]
    if len(pitches) < 5 or not hold["dominant_peak_samples"]:
        raise ValueError("Missing EG1 pitch diagnostics")
    max_attack_cents = max(pitches, key=lambda p: abs(p["dominant_peak_difference_cents"]))
    report = {
        "experiment": "P194 absolute-spectrum and EG1 attribution (no audio changes)",
        "compared_seconds": p97["compared_seconds"],
        "p97_global_gain_db": match_db,
        "p97_active_seconds_verified": len(every_second),
        "global_spectrum_reproduced": [
            {"band_hz": "%d-%d" % (lo, hi),
             "native_minus_hardware_db": round(float(deltas[i]), 3)}
            for i, (lo, hi) in enumerate(BANDS)],
        "low_band_50_200_net_excess_power": total_delta,
        "low_band_50_200_hardware_power": float(global_ref[0]),
        "low_band_50_200_native_matched_power": float(global_emu[0]),
        "sections_sorted_by_absolute_net_excess": ranked,
        "seconds_sorted_by_absolute_net_excess": details,
        "eg1_original_p102_attack_frequency_points": pitches,
        "eg1_original_p102_hold_frequency_points": hold["dominant_peak_samples"],
        "eg1_peak_abs_attack_cents": max_attack_cents,
        "limitations": [
            "Reference was analog 48kHz; no equal-rate digital S/PDIF dry capture.",
            "Exact FFT windowing, channels, activity threshold and one global gain from P97.",
            "A section's huge ratio with near-zero source energy can be harmless; rank by absolute power, not ratio.",
            "Section assignment by 1-second window midpoint; windows at section boundaries may mix adjacent sounds.",
            "EG1 is the dominant spectral peak, not proven fundamental; cross-confirm against hardware and register traces before DSP retuning.",
            "No individual hardware sample clock, latency drift or analog response characterization."
        ],
    }
    Path(a.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("P194 verified global 50-200 Hz error: %.3f dB (%d active 1s windows)" %
          (deltas[0], len(every_second)))
    print("P194 top contributions to actual low-band excess:")
    for row in ranked[:10]:
        print("P194  %-26s %+7.2f%%  HW share %7.2f%%   local %8s dB" %
              (row["test"], row["contribution_to_global_excess_percent"],
               row["hardware_fraction_of_global_50_200_power"] * 100,
               row["local_50_200_error_db"]))
    print("P194 max EG1 attack dominant-peak delta %+0.2f cents at %.3fs "
          "(no sample-aligned fundamental assertion)" %
          (max_attack_cents["dominant_peak_difference_cents"],
           max_attack_cents["t"]))


if __name__ == "__main__":
    main()
