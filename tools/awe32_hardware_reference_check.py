#!/usr/bin/env python3
"""Evidence check against public recordings of an actual Sound Blaster AWE32.

The historical test card has a broken *dry right* channel. Only the LEFT
channel is compared. Each recording is a 30s, level-matched, time-aligned
excerpt; the card is not the user's Synth 512 Bank.sf2. Metrics measure
agreement and document limitations; they do NOT certify 1:1 fidelity.

Public data from turican0/AWE32Emu 'sources' branch, immutable commit;
the six large recordings stay outside 125A's repo and CI artifacts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import soundfile as sf
from scipy import signal

SRC_SHA = "9ae2217b92af72f706c9631679cd43c3afff507f"
FILES = {
    "menu": {
        "card": ("demos/mc2_menu_card.flac", "1ccc92765457cc940447bc9b8a2920a53f331763"),
        "emu": ("demos/mc2_menu_awe32emu.flac", "21fa0941601bc316d435735d9f35add6cda8a927"),
    },
    "intro": {
        "card": ("demos/mc2_intro_card.flac", "f1414f2c66bc1daf4b60b8ecc77b50998b16eab0"),
        "emu": ("demos/mc2_intro_awe32emu.flac", "fca74927d45e8e01f5a0d3816c5e6a44a3d79b5f"),
    },
    "level1": {
        "card": ("demos/mc2_level1_card.flac", "e07489e23b571ce5866aaa8ff435385c27a35bcb"),
        "emu": ("demos/mc2_level1_awe32emu.flac", "e90daeab7b24d675c0b980c20d3408a261eb305f"),
    },
}
# Spectrum bands are broad enough to be meaningful despite analog transfer
# functions. The level-1 capture uses a darker capture chain than menu/intro.
BANDS = ((80, 200), (200, 800), (800, 3000), (3000, 8000), (8000, 10500))


def download(path: str, git_sha: str, target: Path) -> None:
    url = f"https://raw.githubusercontent.com/turican0/AWE32Emu/{SRC_SHA}/{path}"
    request = Request(url, headers={"User-Agent": "125A-hardware-evidence-check"})
    with urlopen(request, timeout=90) as resp, target.open("wb") as f:
        while part := resp.read(2 * 1024 * 1024):
            f.write(part)
    payload = target.read_bytes()
    digest = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
    if digest != git_sha:
        raise ValueError(f"{path}: unexpected Git blob hash {digest} != {git_sha}")


def audio(path: Path) -> tuple[np.ndarray, int]:
    arr, sr = sf.read(path, dtype="float32", always_2d=True)
    if arr.shape[1] != 2:
        raise ValueError(f"{path}: expected stereo")
    return arr[:, 0].astype(np.float64), int(sr)


def envelope(x: np.ndarray, sr: int) -> np.ndarray:
    # 10ms RMS hops: robust to analog phase / DAC differences
    hop = max(1, round(sr / 100))
    n = len(x) // hop
    if n < 20:
        raise ValueError("audio too short")
    return np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1))


def pair_metrics(card_path: Path, emu_path: Path) -> dict:
    card, sr = audio(card_path)
    emu, er = audio(emu_path)
    if er != sr:
        g = math.gcd(sr, er)
        emu = signal.resample_poly(emu, sr // g, er // g)
    # Limit to the matched 30-second excerpt; existing files are aligned by
    # original author but allow small additional envelope lag.
    card = card[:30 * sr]
    emu = emu[:30 * sr]
    cenv = envelope(card, sr)
    eenv = envelope(emu, sr)
    cenv -= np.mean(cenv)
    eenv -= np.mean(eenv)
    corr = signal.correlate(cenv, eenv, mode="full", method="fft")
    lags = signal.correlation_lags(len(cenv), len(eenv), mode="full")
    valid = np.abs(lags) <= 200  # +/- 2 seconds, 10-ms units
    lag_hops = int(lags[valid][np.argmax(corr[valid])])
    offset = int(round(lag_hops * sr / 100))
    # Positive offset means the physical-card audio is later than the emulator.
    if offset > 0:
        card = card[offset:]
    elif offset < 0:
        emu = emu[-offset:]
    size = min(len(card), len(emu))
    card, emu = card[:size], emu[:size]
    # The upstream excerpts have 0.5s fades; skip beginning and end.
    trim = int(.6 * sr)
    if size <= 2 * trim:
        raise ValueError("aligned pair too short")
    card, emu = card[trim:-trim], emu[trim:-trim]

    # Card recording may have an unknown analog frequency response; compare
    # source-level envelopes and relative band energy rather than samples.
    ce, ee = envelope(card, sr), envelope(emu, sr)
    ce, ee = ce[:min(len(ce), len(ee))], ee[:min(len(ce), len(ee))]
    env_corr = float(np.corrcoef(ce, ee)[0, 1])
    amp_ratio = float(np.sqrt(np.mean(card**2)) / np.sqrt(np.mean(emu**2)))
    # Content-weighted wideband difference within each band, adjusted for
    # the overall gain so analog recording volume cannot dominate.
    f, cp = signal.welch(card, fs=sr, nperseg=4096)
    _, ep = signal.welch(emu, fs=sr, nperseg=4096)
    bands = {}
    for lo, hi in BANDS:
        ix = (f >= lo) & (f < min(hi, sr / 2))
        if np.any(ix):
            cpower = float(np.sum(cp[ix]))
            epower = float(np.sum(ep[ix]))
            if epower > 0 and cpower > 0:
                bands[f"{lo}-{hi}Hz"] = round(
                    10 * math.log10(cpower / (epower * amp_ratio**2)), 2
                )
    return {
        "sample_rate_hz": sr,
        "aligned_seconds": round(size / sr, 2),
        "card_delay_relative_to_emu_ms": 10 * lag_hops,
        "left_channel_rms_envelope_correlation": round(env_corr, 4),
        "card_over_emu_rms_db": round(20 * math.log10(amp_ratio), 2),
        "relative_band_differences_db": bands,
        "warning": "Real card right dry output is defective. This is not an SF2 000/007 recording.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="hardware-reference-results.json")
    args = parser.parse_args()
    out = {
        "data_origin": "turican0/AWE32Emu sources branch",
        "data_commit": SRC_SHA,
        "source_readme": "https://github.com/turican0/AWE32Emu/blob/sources/demos/README.md",
        "card": "real Sound Blaster AWE32, DSP 4.13, 8MB RAM, DOS SBAWE32.MDI",
        "user_sf2_not_tested_against_this_hardware": True,
        "not_1_to_1_proof": True,
        "pairs": {},
    }
    with tempfile.TemporaryDirectory(prefix="125a-awe32-real-hardware-") as temp:
        root = Path(temp)
        for name, items in FILES.items():
            paths = {}
            for role in ("card", "emu"):
                filename, sha = items[role]
                p = root / f"{name}_{role}.flac"
                download(filename, sha, p)
                paths[role] = p
            result = pair_metrics(paths["card"], paths["emu"])
            out["pairs"][name] = result
            print(name, json.dumps(result, sort_keys=True), flush=True)
    Path(args.output).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    print("EVIDENCE MEASURED: physical card against upstream AWE32Emu.\n"
          "NOT ESTABLISHED: complete 1:1 fidelity of user's 125A VST3 and SF2.", flush=True)


if __name__ == "__main__":
    main()
