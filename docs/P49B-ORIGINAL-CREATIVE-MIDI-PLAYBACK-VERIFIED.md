# P49b — Windows 95 original Creative AWE32 PnP MIDI note playback verified

Research outcome, 2026-11-01. P26 sound engine unchanged.

## Original-driver guest playback run

- [GitHub Actions run 41351601157](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41351601157) — SUCCESS (all runner steps).
- Windows95 guest software: original Creative AWE32/AWEMAN drivers staged via original Creative INF, with 86Box `sbawe32_pnp` configured. The previous P48b screenshot shows native Windows95 `New Hardware Found — Creative Advanced Wave Effects Synthesis for AWE 32` and desktop.
- `P49-P0.MID`: original, programmatically generated Standard MIDI File Type 0, GM program 0 on MIDI channel 1, note 48, velocity 100, duration 2 seconds at 120 BPM. No original songs, SF2 samples or proprietary audio were distributed.
- `p49-midi-player-initial.png` screenshot: original Windows95 Media Player displays **P49-p0.mid - Media Player (playing)**. `p49-midi-player-after4s.png` shows **Media Player (stopped)** at 02.00 seconds.
- Original Media Player playback was triggered via `C:\WINDOWS\MPLAYER.EXE /play C:\AWE32\P49-P0.MID`; Microsoft historical KB126869 documents `/play` for the 16-bit MPLAYER.
- Controlled emulated EMU8000 I/O logger measured 47,197 raw writes just before launching this MIDI fixture and 47,360 after, **net +163**. Pointer-kind count after: 44,900; data-kind after: 2,460. P48b baseline before playback: 44,824 pointer-kind and 2,372 data-kind. Kind deltas: **+76 pointer, +88 data**, with one line outside simple kind classification.
- 86Box emulated Wavetable stream: **44,100 Hz**, 5-second analysis window, **peak -32.8 dBFS**, **RMS -49.7 dBFS**. Main and OPL Music streams remained at -120.0 dBFS. This independently confirms a virtual wavetable audio signal during the test.
- Prior P49 run 41350627251 opened the identical MIDI file but did **not** send `/play`: Media Player stopped, no new EMU8000 register writes and all relevant audio streams at -120.0 dBFS.

## What this establishes

The original Windows95 multimedia stack can open and play the deterministic MIDI note after the Creative AWE32 PnP hardware is discovered; this coincides with an increase in emulated EMU8000 register accesses and with non-silent wavetable audio. This makes original Creative driver MIDI synthesis in the 86Box reference **strongly supported**. A precise module-level attribution to `SBAWE.VXD` is not independently established, and these are **emulated**, not real-AWE32-hardware I/O traces.

## What remains

1. Reproduce the same test with program 7. Neither P0 nor P7 matches an arbitrary user Bass SF2 patch until exact instrument/bank/SF2 mapping is verified.
2. Recover/parse per-write voice register transactions around controlled note on/off, with idle baseline subtraction, and compare only after exact SF2 file and patch identity are specified.
3. Separate sound output comparison from register/driver behavior. Virtual 86Box output is not a 1:1 physical AWE32 proof.

No guest Win95 image, Creative proprietary binaries, 86Box ROMs, generated WAV audio, user SF2 or private source data were committed or uploaded.
