#!/usr/bin/env python3
"""P60: infer original Creative Win95 SF2 sample upload format from EMU8000 I/O.

The fixture is a newly GENERATED sine test SF2, never a user/private SoundFont.
Read private raw CSV within ephemeral runner; emit only statistics in the
parent JSON report. No raw upload words, sample/audio data, SF2, driver, ROM or
guest disk leave CI. This is a hypothesis test, NOT a hardware gold standard.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from p55_stage_generated_sf2 import make_sf2


def _signed16(n: int) -> int:
    return n - 65536 if n >= 32768 else n


def _pre_emphasis_win95(samples: list[int]) -> list[int]:
    out = list(samples)
    # Mirrors observed SF1 Creative Win95 formula. Whether the original
    # Win95 driver also applies it to SF2 is the *question* under test.
    end = 4410 - 3
    for i in range(end):
        prev = samples[i - 1] if i else 0
        nxt = samples[i + 1]
        num = 6 * samples[i] - prev - nxt
        out[i] = max(-32768, min(32767,
            (num >> 3) if num >= 0 else -((-num + 7) >> 3)))
    return out


def _expected_pcm() -> list[int]:
    sf2 = make_sf2(wideband=True)
    i = sf2.find(b"smpl")
    if i < 0:
        raise AssertionError("Generated SF2 contains no smpl chunk")
    n = int.from_bytes(sf2[i + 4:i + 8], "little")
    samples = [_signed16(int.from_bytes(sf2[i+8+j:i+10+j], "little"))
               for j in range(0, n, 2)]
    if len(samples) != 4456:
        raise AssertionError("Unexpected generated SoundFont test payload")
    return samples


def analyze(trace: Path, start_count: int, end_count: int) -> dict:
    input_pcm = _expected_pcm()
    filtered_pcm = _pre_emphasis_win95(input_pcm)
    half_pcm = [int(round(x/2.0)) for x in input_pcm]
    words = []
    with trace.open("r", encoding="utf8", errors="replace") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx < start_count:
                continue
            if idx >= end_count:
                break
            if (row.get("kind") == "data" and row.get("reg") == "1"
                and row.get("voice") == "26"
                and row.get("port", "").lower() in ("0x0a20", "0x0a22")):
                words.append(_signed16(int(row["value"], 16)))
    summary = {"phase": "P62", "test_source": "generated 440Hz + 4400Hz + 12000Hz wideband SF2, not user SF2",
        "source_pcm_words":len(input_pcm),
        "original_driver_memory_write_words":len(words),
        "raw_sf2_bytes_publicly_uploaded":False,
        "raw_emu8000_memory_trace_publicly_uploaded":False,
        "driver_syntax": "original Win95 Creative AWECP32 through 86Box EMU8000",
        "hypotheses": ["unmodified SF2 PCM", "uniform half-amplitude SF2 PCM", "SF1-style Win95 pre-emphasis /8"]}
    if len(words) < 256:
        summary["result"] = "Insufficient EMU8000 RAM writes for upload comparison"
        return summary
    # Compare limited *numerical* statistics after aligning a 440Hz sine.
    # Actual sample loader may write a few alignment words first/last.
    n = min(3200, len(words), 4410)
    stride=4
    limit=max(0, min(len(words)-n, 2048))
    candidates = {
        "raw": input_pcm[:n:stride],
        "half_gain": half_pcm[:n:stride],
        "preemphasis8": filtered_pcm[:n:stride],
    }
    rankings = {key: [] for key in candidates}
    # The P60 first sample alignment was word 17, with 36 extra words
    # relative to the actual smpl chunk. Allow a 128-word shift to account
    # for guard/reserve effects without confusing nonlocal audio matches.
    for offset in range(0,min(limit,128)+1):
        x=words[offset:offset+n:stride]
        if len(x)<128:
            continue
        for key,y in candidates.items():
            err=sum((v-s)**2 for v,s in zip(x,y))/len(x)
            rankings[key].append((err,offset))
    if not all(rankings.values()):
        summary["result"]="No sufficient continuous memory transfer segment"
        return summary
    best = {key:min(values,key=lambda pair:pair[0])
            for key,values in rankings.items()}
    closest = min(best,key=lambda key:best[key][0])
    score, offset = best[closest]
    summary.update({
        "sample_window_words":n,
        "chosen_model":closest,
        "best_contiguous_word_offset":offset,
        "unmodified_pcm_rmse_units":round(math.sqrt(best["raw"][0]),2),
        "half_amplitude_pcm_rmse_units":round(math.sqrt(best["half_gain"][0]),2),
        "win95_sf1_style_preemphasis_rmse_units":round(math.sqrt(best["preemphasis8"][0]),2),
        "best_alignment_by_model": {k:v[1] for k,v in best.items()},
        "best_rmse_units":round(math.sqrt(score),2),
        "analysis_scope_note":"Wideband ORIGINAL synthetic bank, never private user SF2",
        "discriminator": "high-frequency dependence distinguishes Creative pre-emphasis from a uniform half-gain"
    })
    # A close numerical fit, not just smaller error, is required to call
    # either upload model confirmed.
    if score < 5.0:
        summary["fit"]= "Bit-level/near-bit-level agreement"
    elif score < 150.0**2:
        summary["fit"]= "Good numeric agreement"
    else:
        summary["fit"]= "INCONCLUSIVE: neither model fits the captured writes"
    return summary
