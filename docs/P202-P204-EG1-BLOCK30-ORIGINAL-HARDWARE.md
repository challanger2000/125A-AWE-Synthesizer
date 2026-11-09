# P202–P204: Original AWE32 hardware Block-30 evidence vs 125A AWE64 EG1 discrepancy

**Research date:** 2026-11-09. **Production:** unchanged; last audio-code SHA `2f986648d0507ba97c804b483ce00021a2f656fe`. The AWE32Emu project explicitly separates chip calibration (its original AWE32 card) and SoundFont/Creative driver emulation. Do not conflate those hardware populations or recording paths.

## 1. P202: SF2 Win95 register is outside the tested hardware range

- Original audio/MIDI/SF2: SHA-pinned SoundFont Specification Test v3.0; original program 0 MIDI note **59**, single valid SF2 instrument zone **sampleID=43**, generator **`modEnvToPitch=1200`**, **`attackModEnv=0` timecents = 1.0s**.
- Actual `SoundFont::MakeVoiceParams` on Win95 passes the generator to `AttackRateFromSf2Timecents`, itself documented as an original `SBAWE.VXD` (C119C1D9) reverse-engineered integer expression. For timecents 0: `q=(0+500)/150=3`, `mant=((~3)&7)|8=12`, `shift=3/8=0`, so `ATKHLD & 0x7F = 12 (0x0C)`.
- Original AWETST25 hardware test `BlockModEnvTime` in `tools/awetest/AWETEST.C` uses **exactly** `{0x10,0x14,0x18,0x20,0x24,0x2C,0x34,0x3C}` for **direct chip registers**. It uses `SMP_NOISE`, `cutoff=64`, `PEFE=0x7F` (mod envelope to filter), not the CT4390 SF2 `PEFE` pitch destination.
- The original upstream `AWE32Emu/src/Emu8000.cpp` says these eight filtered-noise measurements imply strongly convex brightness, ≈0.45 at 0.05 normalized time and ≈0.76 at 0.10 normalized time; brightness above ~0.7 saturates. It models this as `1-(1-x)^13.5` and uses the same curve in the 86Box-derived chip engine. These are **approximate brightness-inversion measurements**, not readouts of the actual chip envelope register.
- **Consequence:** original separate AWE32 hardware block30 gives no direct rate-0x0C control. Applying a single globally tuned chip envelope based on one AWE64 Gold test would overrule independently measured `0x10..0x3C` chip evidence. Conversely, the original block30 cannot be used to assert exact `0x0C` chip behavior.

The audit [GitHub Actions #42684897965](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42684897965) **SUCCESS** and artifact [P202 metadata](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42684897965/artifacts/13703897648). The original upstream **main** commit `17b0578fe59909dfaa784b5531d6d1a3a80729ce` and original SF2 are pinned and Git-blob-verified; read-only parser `tools/p202_block30_provenance.py` checks instrument/preset linkage, actual converter formulas and original test rates. Sources: [original AWETEST.C](https://github.com/turican0/AWE32Emu/blob/17b0578fe59909dfaa784b5531d6d1a3a80729ce/tools/awetest/AWETEST.C) and [original chip envelope model](https://github.com/turican0/AWE32Emu/blob/17b0578fe59909dfaa784b5531d6d1a3a80729ce/AWE32Emu/src/Emu8000.cpp).

## 2. P203: Narrow candidate as a controlled negative-regression check, NOT a silicon proof

The prior native-only P201 correction `−0.30*x*(1−x)` improved a *single CT4390 SF2 EG1 pitch attack* from **81.85 to 29.47 cents** median absolute error. P203 instead applies this correction **ONLY if the actual ATKHLD modulation attack register is below `0x10`**. The original hardware-calibrated `0x10..0x3C` modes and all faster rates retain the original `1-(1-x)^13.5` calculation. This is a *research hypothesis*, not an original chip-rule reconstruction.

[P203 full 264s original CT4390 comparison #42685310513](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42685310513) **SUCCESS**, including original Creative SF2 P90, independent P200 pitch tracker, P102/P103/P105/P194/P195/P197/P199 regression metrics, and a **negative compile test that actively rejects P203 when VST3=ON**. The independent baseline rebuilt after the modified helper signature, [#42685155427](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42685155427), also **SUCCESS**.

| Indicator | Default chip curve | P203 slow-only hypothesis |
|---|---:|---:|
| Original CT4390 note59 median abs EG1 attack-pitch discrepancy | **81.85 cents** | **29.47 cents** |
| Hold-pitch discrepancy | +3.64 cents | +3.64 cents |
| Sustain-pitch discrepancy | −1.49 cents | −1.49 cents |
| 264s overall log-envelope correlation | 0.95283 | 0.95282 |
| Level-matched 50–200Hz frequency band | −0.347 dB | −0.347 dB |
| Level-matched 200–500Hz band | −0.368 dB | −0.367 dB |
| All AWETST25-tested chip rates `>=0x10` | Default shape | **Default shape by conditional construction** |
| 125A production VST3 | Untouched | **Untouched; build forbidden** |

This narrows the scope and avoids mathematical changes to the eight tested hardware rates, but **does not prove** that all sub-0x10 EG1 chip rates share the candidate curve. Other bank programs and mod-to-filter at low rates remain unverified. The 264s aggregate envelope/band metrics are insensitive to short individual-note failures; they do not replace a per-register hardware reference.

Artifact [P203 CT4390 pitch and full-run metrics](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42685310513/artifacts/13705190866).

## 3. P204: Genuine AWETST25 recorded card audio, not a synthetic reconstruction

Upstream keeps the original physical hardware measurements separately in its `sources` branch, commit `9ae2217b92af72f706c9631679cd43c3afff507f`. The original `recordings/2026-09-12/recc/awetest.log` contains the eight exact Block-30 note times, original capture sample frames and actual register rates. P204 downloaded and SHA-verified **`recc138.flac`**, **`recc139.flac`**, and **`recc140.flac`** (about 3.7 MB total), which together cover all eight modulation-attack tones. Metadata is calculated over the original hardware recordings, **not a rendered emulator**.

Read-only `tools/p204_original_block30_audio.py` computes 256-bin Hann FFT-frame log-brightness = energy at 3–12kHz / energy at 200–1500Hz (5ms hop, 5-frame smoothing), relative to its own fixed post-attack plateau. Timestamp comes only from original `awetest.log`; no per-note phase alignment is fitted.

| Real AWE32 raw ATKHLD mod attack | Original nominal time T | Brightness at 0.05T (dB relative post-attack) | At 0.10T | At 0.20T |
|---|---:|---:|---:|---:|
| `0x10` | 0.742 s | −21.96 | −5.79 | −0.71 |
| `0x14` | 0.594 s | −22.79 | −5.82 | +0.10 |
| `0x18` | 0.495 s | −22.18 | −5.97 | −3.52 |
| `0x20` | 0.371 s | −22.98 | −5.46 | −0.49 |
| `0x24` | 0.297 s | −23.08 | −6.39 | +0.11 |
| `0x2C` | 0.212 s | −22.32 | −7.86 | +0.64 |
| `0x34` | 0.148 s | −19.77 | −10.58 | +0.90 |
| `0x3C` | 0.106 s | −18.15 | −12.17 | +0.04 |

**Interpretation:** the actual hardware audio has a sharply increasing filter brightness very early, near its post-attack timbral plateau already by ~0.2T for most rates. At short rates, 25ms smoothing spans much of the first 0.1T and attenuates measured transients; source recording noise and sample/filter coloration also limit precision. This measurement confirms the original hardware data exist and can be independently audited. It **does not** directly invert the internal recording's compressor to a silicon envelope value or establish 0x0C behavior. The original internal capture path is **non-linear**, and the hardware AWETST block uses **AWE32 filter-modulated noise**, not the **AWE64 Gold pitch-modulated single-sample SF2** used by P200.

[P204 actual physical sound-card source analysis #42686799522](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42686799522) **SUCCESS**; [derived numerical JSON artifact](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42686799522/artifacts/13705741451). Source audio remains only on the original AWE32Emu archive, never in our repo or exported artifact. The documented verification code used the complete 40-character Git blob hashes; the first diagnostic attempt had a one-character transcription error in the `recc139` expected hash and was rerun with exact original hash verification before accepting any figures.

## 4. Practical engineering decision

**P202–P204 research PASS, no product DSP change authorized.** We now know that (a) SF2/Win95 already generates original rate `0x0C` by original-VXD arithmetic; (b) upstream Block30 direct hardware model was established over eight **different/faster** attack rates; (c) a carefully constrained correction for slower rates significantly improves *one* CT4390 note without mathematically altering hardware-tested rates; and (d) the genuine AWE32 original source audio can be read with timestamp and recording-path limitations.

It is still not shown that the real chip uses the P203 rate-dependent rule; an original **slow rate 0x0C pitch and filter reference**, ideally from the same silicon hardware/setup, is the missing independent control. Until that evidence exists, **do not change** default EMU8000 mod attack, correct Creative Win95 `ATKHLD` driver arithmetic, create per-preset special cases, or risk breaking SF1/ROM banks.

Production last tested P198 source SHA [`2f986648`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/2f986648d0507ba97c804b483ce00021a2f656fe), [full Windows #42593301776](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42593301776) 67/67 CTests, 537/537 VST3 validator, 99/99 true GUI actions, independent Test Lab TECHNICAL_PASS, 0/14,400 lab RT deadline misses. Current branch additions are only Markdown and do not warrant re-running identical VST3 binaries. Owner's real Studio Pro/ASIO, private ROM/77-preset bank, independent FULL AUDIT and commercial release remain open (NO-GO).
