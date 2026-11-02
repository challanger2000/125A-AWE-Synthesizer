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
    sf2 = make_sf2()
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
    summary = {"phase": "P60", "test_source": "generated P55 440Hz sine, not user SF2",
        "source_pcm_words":len(input_pcm),
        "original_driver_memory_write_words":len(words),
        "raw_sf2_bytes_publicly_uploaded":False,
        "raw_emu8000_memory_trace_publicly_uploaded":False,
        "driver_syntax": "original Win95 Creative AWECP32 through 86Box EMU8000",
        "hypotheses": ["unmodified SF2 PCM", "SF1-style Win95 pre-emphasis /8"]}
    if len(words) < 256:
        summary["result"] = "Insufficient EMU8000 RAM writes for upload comparison"
        return summary
    # Compare limited *numerical* statistics after aligning a 440Hz sine.
    # Actual sample loader may write a few alignment words first/last.
    n = min(3200, len(words), 4410)
    stride=4
    limit=max(0, min(len(words)-n, 2048))
    rankings=[]
    for offset in range(0,limit+1):
        x=words[offset:offset+n:stride]
        if len(x)<128:
            continue
        ys=(input_pcm[:n:stride],filtered_pcm[:n:stride])
        err=[sum((v-s)**2 for v,s in zip(x,y))/len(x) for y in ys]
        rankings.append((min(err),offset,err[0],err[1]))
    if not rankings:
        summary["result"]="No sufficient continuous memory transfer segment"
        return summary
    score,offset,rawerr,preerr=min(rankings,key=lambda z:z[0])
    summary.update({
        "sample_window_words":n,
        "best_contiguous_word_offset":offset,
        "unmodified_pcm_rmse_units":round(math.sqrt(rawerr),2),
        "win95_sf1_style_preemphasis_rmse_units":round(math.sqrt(preerr),2),
        "closer_hypothesis":("unmodified SF2 PCM" if rawerr < preerr
                             else "SF1-style Win95 pre-emphasis /8"),
        "best_rmse_units":round(math.sqrt(score),2),
        "analysis_scope_note":"Only source test sine; not the original user bass bank"
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
