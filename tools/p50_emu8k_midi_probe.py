#!/usr/bin/env python3
"""P50: measure Win95 Creative AWE32 PnP MIDI playback for GM programs 0 and 7.

The input MIDI fixtures are original test data; they are NOT the user's
original SoundFont patches. This module never synthesizes notes via 86Box
synthetic I/O. Guest Win95 MPLAYER.EXE invokes the MIDI stack.
"""
from __future__ import annotations

import csv
import hashlib
from collections import Counter
from pathlib import Path

from p47_86box_emu8k_smoke import send


def raw_writes(path: Path) -> list[str]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf8", errors="replace") as f:
        lines = f.read().splitlines()
    if not lines or lines[0] != "sequence,wc,port,value,pointer,reg,voice,kind":
        raise ValueError("EMU8000 logger CSV header mismatch")
    return lines[1:]


def summarize_delta(lines: list[str], start: int) -> dict:
    if not 0 <= start <= len(lines):
        raise ValueError("Invalid I/O baseline")
    writes = lines[start:]
    parsed = list(csv.DictReader(
        ["sequence,wc,port,value,pointer,reg,voice,kind", *writes]
    ))
    kinds = Counter(row["kind"] for row in parsed)
    reg_hist = Counter(row["reg"] for row in parsed if row["kind"] == "data")
    voice_hist = Counter(row["voice"] for row in parsed if row["kind"] == "data")
    port_hist = Counter(row["port"] for row in parsed)
    return {
        "raw_write_count": len(writes),
        "pointer_write_count": kinds.get("pointer", 0),
        "data_write_count": kinds.get("data", 0),
        "other_write_count": len(writes)-kinds.get("pointer",0)-kinds.get("data",0),
        "data_reg_histogram": dict(sorted(reg_hist.items())),
        "data_voice_histogram": dict(sorted(voice_hist.items())),
        "port_histogram": dict(sorted(port_hist.items())),
        "trace_sha256": hashlib.sha256(
            ("\n".join(writes)+"\n").encode("utf8")
        ).hexdigest(),
        # No raw ROM, sample data, proprietary driver files or SF2 data
        # are copied into this JSON. The raw CSV stays on ephemeral runner.
    }


def compact_level(response: dict) -> dict:
    """Only meaningful numeric sound metrics, no encoded audio payload."""
    streams = response.get("streams", {})
    out = {}
    for stream in ("wavetable", "music", "main"):
        value = streams.get(stream)
        if isinstance(value, dict):
            out[stream] = {k: value.get(k) for k in (
                "peak_db", "rms_db", "frames", "rate"
            )}
    return out


def play(
    conn, out_dir: Path, trace: Path, program: int,
    *, key, type_path, screenshot, report: dict
) -> dict:
    if program not in (0, 7):
        raise ValueError("Only known P49 fixtures 0/7 are staged")
    prefix = f"p50-p{program}"
    name = f"c:\\awe32\\p49-p{program}.mid"
    command = f"c:\\windows\\mplayer.exe /play {name}"

    # After P0 completion, the verified Win95 Media Player is foreground.
    # Close it before launching P7 so two instances do not share MIDI routing.
    if program == 7:
        send(conn, "key down 0x38 0x3e")  # left Alt + F4
        send(conn, "key up 0x3e 0x38")
        send(conn, "step 350")
        screenshot(conn, out_dir, f"{prefix}-after-previous-close.png", report)

    # Start -> Run uses the same screenshot-confirmed navigation as P49.
    send(conn, "key down 0x1d 0x01")  # Ctrl+Esc
    send(conn, "key up 0x01 0x1d")
    send(conn, "step 300")
    key(conn, 0x13)                   # Run menu item "R"
    send(conn, "step 500")
    screenshot(conn, out_dir, f"{prefix}-run-dialog.png", report)
    type_path(conn, command)
    screenshot(conn, out_dir, f"{prefix}-command.png", report)

    before = raw_writes(trace)
    trial = {
        "program_zero_based": program,
        "gm_program_number": program + 1,
        "fixture": name,
        "midi_note": 48, "velocity": 100,
        "expected_duration_seconds": 2,
        "raw_writes_before": len(before),
        "playback_confirmed_by_screen": False,  # images require examination
        "audio_source_proven_by_guest": False,  # sound card routing needs audit
    }
    try:
        send(conn, "audio start")
        trial["audio_recording_enabled"] = True
    except RuntimeError as exc:
        trial["audio_start_error"] = str(exc)

    key(conn, 0x1c)                   # Enter in Run dialog
    send(conn, "step 1000")
    screenshot(conn, out_dir, f"{prefix}-player-playing.png", report)
    trial["level_first_second"] = compact_level(send(conn, "audio level 1000"))
    trial["writes_after_first_second"] = len(raw_writes(trace))-len(before)
    send(conn, "step 4000")
    screenshot(conn, out_dir, f"{prefix}-player-finished.png", report)
    trial["level_whole_five_seconds"] = compact_level(send(conn, "audio level 5000"))
    try:
        summary = send(conn, "audio stop")
        trial["audio_stop_segment_count"] = len(summary.get("segments", []))
    except RuntimeError as exc:
        trial["audio_stop_error"] = str(exc)
    after = raw_writes(trace)
    trial.update(summarize_delta(after, len(before)))
    return trial
