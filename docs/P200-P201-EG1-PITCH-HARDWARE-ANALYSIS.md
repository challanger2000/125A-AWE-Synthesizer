# P200/P201 – EG1 modulation-to-pitch attack: real CT4390 measurements and bounded experiments

**Date:** 2026-11-09. **Source oracle:** original SHA-pinned SoundFont Specification Test v3.0, 264s MIDI, original program 0 note 59 (one valid preset-linked instrument zone, sampleID 43, `modEnvToPitch=1200`). AWE64 Gold CT4390 analog reference 48kHz FLAC, native 86Box-derived 44.1kHz EMU8000 with P193 historically matched FX sends/returns. No individual audio gain fitting or pitch recalibration, no modifications to recorded/original reference material. All P201 changes live **only** in the `research/p193-ct4390-fidelity` branch, guarded by `AWE125_P193_CT4390_REFERENCE_FX`, and cannot build with `125A_BUILD_VST3=ON`.

## P200 – Spectral peak is confirmed pitch, not a harmonic switch

[P200 full reference run #42679595500](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42679595500), SUCCESS. The new `tools/p200_eg1_pitch_tracker.py` independently estimates pitch with (a) two FFT windows of 96ms/160ms and (b) 96ms autocorrelation. Bins with >18 cents FFT window disagreement or >35 cents spectral-vs-ACF disagreement are rejected. Results validated in 9/10 attack and 10/10 hold/decay/sustain bins; original MIDI exact 9.5s ON/14.5s OFF and original SF2 linked zone were independently checked. No dynamic time warping; test shifts `-23,0,+23ms` are fixed beforehand from the independent P199 volume-release comparison.

| Original EG1 phase | Native minus CT4390, 0ms median signed | Median abs | Analysis-only comparison at independent P199 lag |
|---|---:|---:|---|
| Attack, 10.64..11.44 s | **+81.85 cents** | **81.85** | -23ms gives +67.52 / 67.52 cents |
| Hold | +3.64 | 3.64 | unchanged |
| Decay | -32.87 | 32.87 | -23ms gives -22.86 cents |
| Sustain | -1.49 | 1.49 | unchanged |
| Release | +24.75 | 24.75 | +23ms gives -3.21 / 3.21 cents |

The ATTACK pitch sweep reaches the stable high note **too quickly** in the emulator. It is not an artefact of selecting a stronger spectral harmonic or the known 23ms analog reference capture delay. The **absolute stable note pitch** is already very close to real CT4390, so a global pitch adjustment is unjustified.

At original 10.80s the dominant frequencies are 676.36Hz hardware / 723.60Hz native; the independent P200 frequency ridge independently found 674.69/721.89Hz. At hold the note is 738.63Hz hardware / 740.18Hz native.

## P201 – Native-only falsification and candidate curve sweep

The default current source has an EG1 modulation attack shape `1-(1-x)^13.5`, derived separately in upstream AWE32Emu from hardware Block 30, and shared by the pitch and filter EG1 chip. It must not be replaced globally just to fit a single commercial SoundFont note. P201 introduces an **optional research-only** CMake flag `AWE125_P201_MOD_ATTACK_SHAPE`, fail-closed if VST3 is ON or if P193 reference mode is OFF. The default **still compiles exactly the old 13.5 curve**.

All variants were tested against the full original 264s analog hardware reference and the independent P200 ridge; each passed native compilation and ordinary driver register tests. The initial broad candidates showed substantial overcorrection, and one early candidate failed a P200 *test assumption* because P199 best lag changed 24->23ms. The analysis validator was corrected to accept release-derived 21..25ms without fitting an attack lag, and the moderate controlled candidates were re-run **both SUCCESS** [#42681282616](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42681282616), with VST3-ban negative control PASS.

| Research-only attack mapping | P200 median signed attack error | Median ABS attack error | Interpretation |
|---|---:|---:|---|
| Current hardware-calibrated Block 30 baseline `1-(1-x)^13.5` | +81.85c | **81.85c** | Early high-pitch arrival |
| Exponent `3` | -143.32c | **143.32c** | Too slow, worse |
| 70/30 fast/slow blend | Not independently certified (initial strict P200 lag assumption) | Not established | P102 peak differences as bad as -270 cents at 10.8s; overcorrected |
| `(1-(1-x)^13.5)-0.40*x*(1-x)` | -43.48c | **43.48c** | Late/low overshoot |
| **`(1-(1-x)^13.5)-0.30*x*(1-x)`** | **-7.41c** | **29.47c** | **Best candidate in this sweep, 64% lower median absolute error** |

The moderate 0.30 candidate retains all stable phases of the note: hold **+3.64c**, decay **-32.87c**, sustain **-1.49c**, and release **+24.75c** before / **-3.21c** after the predeclared +23ms analysis alignment. It improves the attack only. The P97 264s global amplitude envelope correlation remains **0.95282** versus the default **0.95283**; global 50–200Hz P97 level-match error stays **-0.347dB**, 200–500Hz changes by only ~0.001dB. These global metrics are *insensitive* to a short single-note EG1 test and are **not** independent proof of generalized chip correctness.

Default research mode was also rebuilt after adding the optional source flag: [baseline reference CI #42681270766](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42681270766) SUCCESS. Artifact: [P201 candidate 0.30](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42681282616/artifacts/13701939114), candidate 0.40 in the same CI run. The original reference, ROM and matching MIDI were hash-verified, and original ROM was removed from the CI runner at completion.

## Engineering verdict and release boundary

- **Validated flaw:** real CT4390 EG1 modulation-to-pitch ATTACK transient for the specified original SF2 note; stable pitch and the previously measured amplitude release are largely correct. Earlier dominant-peak-only P102 did **not** overstate the transient.
- **Research candidate:** a bounded 0.30 shape correction produces substantial pitch-track improvement at the original single note but is **not an independently silicon-verified replacement** for the global chip mod envelope `Block 30` model.
- **PRODUCTION DECISION: DO NOT PROMOTE YET.** The chip's modulation envelope simultaneously changes pitch **and** filter; the same DSP runs for other banks (including SF1/ROM) with many timings. Only one physically grounded mod-to-pitch test note is available here; no independently captured alternative hardware EG1 attack rate or filter-modulation trajectory to rule out overfitting. A global modification would breach hardware-emulation fidelity without that evidence. Avoid inserting arbitrary sample-specific correction or silently modifying Win95 driver registers whose original binary trace has not confirmed a defect.
- **Preserve** P196 SF2 explicit zero `scaleTuning`, P198 hardware-calibrated SF2 initial attenuation `0.50`, P190 zero%-FX dry contract, P192 RT optimisation, default EG1 Block 30 and all P90 original Creative register vectors.
- Production last tested **audio-code SHA**: [`2f986648`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/2f986648d0507ba97c804b483ce00021a2f656fe), [full Windows #42593301776](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42593301776) SUCCESS, 67/67 CTests, 537/537 VST3 validator, 99/99 GUI, native test lab TECHNICAL_PASS, P190 0/14400 LAB_ONLY. No new production DSP source changes in P200/P201; a fresh Windows build is not required solely for this report.
- Physical target Studio Pro/ASIO and private bank/ROM, independent FULL AUDIT and commercial release remain NOT VERIFIED/NO-GO.

**Next evidence requirement:** independent hardware reference with multiple EG1 attack rates and filter-modulation destinations, preferably instrument register capture or the original AWE32Emu Block 30 trace, to arbitrate whether to replace the global chip curve, adjust SF2/Win95 `ATKHLD` conversion, or leave the current best-generic model. Do not assert that soundfont-specific pitch agreement proves actual silicon envelope implementation.
