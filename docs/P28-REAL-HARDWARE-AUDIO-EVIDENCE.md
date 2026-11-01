# P28 — Physical Sound Blaster AWE32 audio evidence (2026-11-01)

**Verdict: COMPLETE 1:1 PARITY IS NOT PROVEN.** This audit is the first machine-executed comparison in this project's Actions against publicly available **physical AWE32** recordings (instead of only FluidSynth, synthetic inputs, and 86Box self-tests).

## Provenance and reproducibility

- Source: `turican0/AWE32Emu` branch `sources`, pinned commit `9ae2217b92af72f706c9631679cd43c3afff507f`; six FLAC files from `demos/`.
- Every download is validated against its exact Git object SHA-1, so there is no silent file substitution.
- The three AWE32 reference FLACs were captured from a real card running Magic Carpet 2 under DOS with `SBAWE32.MDI`; the matching recordings were rendered with upstream AWE32Emu. Original author had time-aligned and level-matched the pairs.
- The physical test card had **defective dry right output**. We therefore only compare left channels. The level-1 card capture had a distinctly darker recording path. Do not interpret left-channel-only mismatches as proof of a broken stereo renderer.
- Reproducible script: `tools/awe32_hardware_reference_check.py`, workflow `.github/workflows/p28-real-hardware-evidence.yml`. GitHub Actions run [#41279843461](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41279843461): **SUCCESS**.
- No third-party FLAC, user SF2 or wave ROM is committed or republished by our repository; only an evaluation JSON artifact is uploaded.

## Actual measurements

Results from 30-second real-card vs upstream-emulator pairs, including envelope alignment of up to 2s. **RMS-envelope correlation** measures the similarity of changes in loudness through time; it is *not* sample-by-sample correlation and is not a certification of 1:1 timbre.

| Excerpt | RMS-envelope correlation (left) | Card - emulator RMS (dB) | Aligned relative offset |
| --- | ---: | ---: | ---: |
| MC2 intro | **0.8579** | +0.36 dB | +30 ms |
| MC2 menu | **0.3842** | +0.27 dB | 0 ms |
| MC2 level 1 | **0.6687** | -1.17 dB | -20 ms |

Examples of relative spectral-band differences after compensating overall gain:

- Intro: +2.09 dB at 80–200 Hz, +2.12 dB at 200–800 Hz, +2.16 dB at 800–3000 Hz, +1.81 dB at 3000–8000 Hz, +1.29 dB at 8000–10500 Hz.
- Menu: -1.14 dB at 80–200 Hz, +3.03 dB at 200–800 Hz, +4.17 dB at 800–3000 Hz, -0.86 dB at 3000–8000 Hz, +0.22 dB at 8000–10500 Hz.
- Level 1: recording-chain differences noted by original author; the spectral comparison does **not** separate analog recorder response from chip coloration.

These measurements DO NOT prove the complete emulation is bit-exact or perceptually identical. Higher envelope correlation for the intro is evidence of meaningful similarity; the substantially worse menu/level scores warrant investigation if the demand is strict 1:1 fidelity. A broken right channel and recording-chain transfer differences constrain interpretation.

## What can actually be said about the user's P26/P27 bass plugins

1. **Proven** with user's actual Windows P25 and P26 PCM + voice dumps: P26 fixes ~100ms artificial SF2 volume-envelope delay, correct 2/4 layers for programs 000/007, and ROM-backed 86Box chip was used. P27 synthetic audio proves 86Box pan/chorus/reverb routes produce actual signal.
2. **Hardware evidence**: upstream chip implementation was calibrated against an actual card by AWETEST v05–v28. See `upstream/AWE32Emu/docs/re-notes/emu8000_tuning.md`. Relevant measured characteristics include 0.375 dB/attenuation unit, ~0.75 dB/sustain step, 725.8 microseconds delay unit, pitch within 0.82 cent for block 4, measured Chamberlin filter, output gain -1.1 dB, effect tails and hardware interpolation.
3. **Not proven**: whether our P26/27 **Synth 512 Bank.sf2** programs 000/007 match the line output of a real AWE32: there is **no physical-card recording of those exact two SF2 programs under the same MIDI, driver, effects and level conditions**. The comparisons made here use Magic Carpet 2 / `BULLFROG.SBK` / DOS driver, not the user's SF2 or Win95 VXD. AWE32Emu upstream demo WAVs are also from a separate source build; current 125A has some instance-safety changes, so the demos are external validation material rather than an exact binary replay of 125A.

## Development consequence

**No sound-processing changes** are justified purely by these comparisons, and no "1:1 hardware-emulation" or "sound finished" statement should be made for the private VST3 until a direct controlled physical AWE32 test can be performed with the exact bank/presets. Keep P26 as the last measured timbre fix. Future work should investigate the underlying chip's error against controlled AWETEST goldens without using FluidSynth as a hardware oracle.
