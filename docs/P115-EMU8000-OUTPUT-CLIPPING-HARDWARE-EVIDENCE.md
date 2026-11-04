# P115 — EMU8000 output clipping vs measured physical AWE32/AWE64

**Status: evidence comparison completed, private-SF2 hardware parity remains OPEN.**
**Date: 2026-11-04.**
Scope: native 86Box EMU8000 at 44.1 kHz; output int32 to PCM16, not a generic SF2 player's normalisation policy. No sound engine settings were modified for P115.

## 1. Reproducible user-bank evidence (P112 → P113 → P114)

The user ran three separate Windows diagnostics locally with the same private original wave ROM (`awe32.raw`), original GM descriptor (`SYNTHGM.SBK`), and 77-program `Synth 512 Bank.sf2`. Private binary assets, audio and per-preset CSV were **not** uploaded to the public repository.

- **P112:** 77 private SF2 programs, 128 original GM ROM programs, 8 representative drum keys; 213/213 produced measurable held-note audio. This is an audibility test of one valid note per preset, **not** keyboard-wide or hardware-timbre parity.
- **P113:** 11 programs (nine suspect and two controls), MIDI 48, velocities 64/100/127, 1.0 s held + 0.5 s released. Exactly 33 cases. At least one full-scale PCM16 sample in 19 cases.
- **P114:** reads the unmodified 86Box int32 stereo output immediately before the existing PCM16 clamp. 33/33 cases measured. The PCM16 values reproduced all the P113 output meters exactly; the enabled-vs-disabled raw-audit tap passed two sample-bit-exact A/B checks.

| MIDI velocity | Cases | Cases exceeding int16 | Raw samples beyond int16 range |
| --- | ---: | ---: | ---: |
| 64 | 11 | 0 | 0 |
| 100 | 11 | 9 | 59 |
| 127 | 11 | 10 | 3,738 |
| **Total** | **33** | **19** | **3,797** |

Across all tested source levels, the largest native pre-clamp 32-bit sample magnitude was **73,247**, or **+6.9868 dB over 32,768** (in one preset at velocity 127). Nine above-range samples occurred during the release phase of that case. A full-scale PCM16 sample is a *digital-rail observation*; P114 establishes **real pre-clamp range excess** in 19 cases.

The exact P114 16-bit output conversion in `src/engine/Emu8000.cpp` is:

```cpp
out[2u * i]     = static_cast<int16_t>(std::clamp(il, -32768, 32767));
out[2u * i + 1] = static_cast<int16_t>(std::clamp(ir, -32768, 32767));
```

This is in the native 44.1 kHz Box86 path. A test-only raw meter observes `il,ir` before clamping without changing them. A value above 32767 is a software clipping event, but not by itself a historical-hardware fidelity defect.

## 2. Real physical AWE32 saturation and headroom evidence (AWETST28)

The imported **AWE32Emu** hardware characterization `upstream/AWE32Emu/docs/re-notes/emu8000_tuning.md`, section *Measurements on the tester's card (AWETEST v05–v28)*, documents actual Sound Blaster AWE32 tests (DSP 4.13, 8 MB RAM):

- An **external line-out recording** was used for the corrected AWETST28 headroom measurements. Earlier AWETST26/27 recordings had **recorder clipping**, which the experimenter explicitly rejected. AWETST28 used approximately **-24 dBFS acquisition level**.
- An output multiplier of **57737/65536** (~-1.1 dB) after effects and EQ was determined from physical measurements and implemented in the 86Box-derived renderer.
- The measured ceiling relative to one in-phase test voice agrees with the model:

| Coherent voices | Physical AWE32 | Tested upstream render | Render minus physical |
| --- | ---: | ---: | ---: |
| 3 | +8.6 dB | +8.5 dB | -0.1 dB |
| 4 | +9.3 dB | +9.2 dB | -0.1 dB |
| 6 | +9.8 dB | +9.7 dB | -0.1 dB |
| 8 | +10.0 dB | +9.9 dB | -0.1 dB |

The measured saturation/headroom *qualitatively supports* the existence of native output limiting in the physical chip; this is not a per-preset match of the private 77-program bank. The output multiplier is present in our imported `src/engine/snd_emu8k.c` immediately after the effects/EQ output stage, prior to the native PCM16 conversion. The historical comparison concerns an upstream reconstruction; it is not a sample-perfect replay of every current 125A version or driver setting.

**Important:** AWE32/AWE64 digital chip/headroom behavior must not be conflated with a 16-bit analog-recorder ADC maximum. The corrected AWETST28 protocol specifically reduced ADC overload.

## 3. Independent public CT4390 AWE64 Gold physical capture (P97)

`docs/P97-AWE64-GOLD-AUDIO-COMPARISON.md` details a 264-second **real AWE64 Gold CT4390 analog RCA** recording, with the same public SoundFont Spec Test v3.0 MIDI/SF2 played through the current 125A native renderer. The reference is **not** the user's private SF2. Unlike P114's local ROM-backed raw sample inspection, P97 compares different physical and emulated recording chains.

**Control fix already completed:** the initial P97 result was confounded by **native treble index 9 (+7.9 dB)** versus the physical recording's **0 dB EQ**. After programming bass/treble 0 dB for the native test, the published 264s comparison measured native-minus-physical after common level alignment:
- 2–5 kHz **+0.164 dB**; 5–10 kHz **-0.525 dB**; 10–20 kHz **-0.085 dB**.
- Filter cutoff RMS ratio **0.974x**; filter resonance RMS ratio **1.047x**.
- Envelope correlation **0.95402**.
- Reverb section RMS ratio **0.749x** remained open.

[Matched-EQ hardware run #41731911493](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41731911493). Analog captures at 48kHz do not determine exact digital clip points or prove wave-phase parity. The matched P97 public stimulus is different from the private P114 stimulus.

## 4. Comparison and decision

**Demonstrated:**
1. P114's 19/33 outputs mathematically exceed the 16-bit integer limit before conversion.
2. This exact truncation is observable in the software output; there is no missing gain calculation behind P113's rail counts.
3. A separate, carefully gain-controlled **physical AWE32** headroom measurement establishes that the historical hardware exhibits a limiting ceiling under coherent multi-voice summation, reproduced within ~0.1 dB in the upstream renderer.
4. P97 with matched EQ demonstrates meaningful analog similarity on a **different public** SF2/MIDI fixture; it does not prove the particular private-bank clips match a physical card.

**Not demonstrated:** that any particular private SF2 high-velocity tone clips on a physical AWE32/AWE64 at the same sample index, extent, or duration. The historical test uses separate stimulus, effects, driver and sometimes chip model. No available 44.1kHz matched direct S/PDIF reference has been verified for this private SF2.

**Engineering decision:** **DO NOT CHANGE THE DSP** based on the P114 rail readings. Do not add a compensating master attenuator, limiter, automatic preset normalization, or gain decrease to a hardware-emulation path in the absence of a controlled matched physical counterexample. Also do not claim that every P114 peak has been proven authentic to an AWE64.

**Remaining evidence gate:** original CT4390 (or comparable EMU8000 card) 44.1kHz unprocessed digital S/PDIF, with exactly the private SF2 + ROM/SBK setup, MIDI note 48 / velocities 64,100,127, the same note durations and effects/EQ settings, and test-channel output level unmodified. For hardware comparison of proprietary effects, isolate dry/wet. Historical public P97 data cannot substitute for that. If a physical recording is later provided, compare onset/sustain/clip windows after verified clock/latency/level matching; any engine change requires a separate test and demonstrable improvement without breaking P112–P114.

## Sources

- [AWE32Emu original hardware measurement notebook](https://github.com/challanger2000/125A-AWE-Synthesizer/blob/test/p114-raw-32bit-output-audit/upstream/AWE32Emu/docs/re-notes/emu8000_tuning.md)
- [Current native 86Box output and 57737/65536 hardware-matched mixer](https://github.com/challanger2000/125A-AWE-Synthesizer/blob/test/p114-raw-32bit-output-audit/src/engine/snd_emu8k.c)
- [P114 opt-in raw measurement and A/B guard](https://github.com/challanger2000/125A-AWE-Synthesizer/blob/test/p114-raw-32bit-output-audit/tools/p114_raw_32bit_audit.cpp)
- [P97 public AWE64 Gold physical analog comparison and matched EQ](https://github.com/challanger2000/125A-AWE-Synthesizer/blob/test/p114-raw-32bit-output-audit/docs/P97-AWE64-GOLD-AUDIO-COMPARISON.md)
- [P98 external chip/hardware evidence limits](https://github.com/challanger2000/125A-AWE-Synthesizer/blob/test/p114-raw-32bit-output-audit/docs/P98-EXTERNAL-EMU8000-HARDWARE-EVIDENCE.md)

No private assets, audio recordings, user file paths, raw waveform buffers or CSV are committed as part of this report.
