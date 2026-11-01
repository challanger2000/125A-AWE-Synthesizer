# P26 – Audio analysis of real Windows 86Box/EMU8000 recordings (2026-11-01)

This is an evidence report only. Proprietary/user audio files, SoundFont and wave ROM are **not** committed.

## Test provenance

Two Windows x64 P26 renders with the actual user's `Synth 512 Bank.sf2`, externally configured `awe32.raw`, actual 86Box engine, MIDI C3=48, velocity=100, 44,100 Hz, 2 s held notes. Compared with P25 renders and isolated FluidSynth 2.x renders from the same SF2.

The reference FluidSynth settings had `synth.gain=0.2` and separate chorus/reverb-enabled and -disabled renders. **The reference WAV is not authentic AWE32 hardware output and gain/FX algorithms cannot be treated as identical.**

## Verified P26 fix

| Program | P25 onset | P26 onset | P25 ENVVOL | P26 ENVVOL | Layers |
| --- | --- | --- | --- | --- | --- |
| 000 Grungy Ramp Bass | ~120–130 ms | ~20–22 ms | 7F73 | 8000 | 2 |
| 007 TX81Z Lately Bass | ~120 ms | ~20–22 ms | 7F73 | 8000 | 4 |

EMU8000 86Box reports a 980-sample / 22.22-ms FIFO at 44.1 kHz. The P26 onset is consistent with that latency; no extra ~100ms delay remains.

## Audio shape / stereo evidence

Comparing first attack section (~35–250 ms of source after alignment), allowing latency offset around 22–23 ms:

| Program | EMU8000 vs FluidSynth, effects OFF | EMU8000 vs FluidSynth, effects ON |
| --- | --- | --- |
| 000 | ~0.87 waveform correlation per channel | ~0.70 L / ~0.82 R |
| 007 | ~0.98 waveform correlation per channel | effect-dependent, approx -0.72 L / 0.90 R with best signed lag |

This strongly supports correct program/sample selection and basic pitch for program 007. The effect-enabled waveform is deliberately NOT considered a bit-exact hardware reference.

Dry FluidSynth left/right correlations: ~1.000 for 000 and ~0.9985 for 007, effectively mono. Effects-enabled references become wide (L/R correlations approx 0.116 and -0.074, respectively). Windows P26 ROM-backed output is approximately mono (L/R correlations ~0.9999 and ~0.9996). **Do not misdiagnose stereo support based solely on FluidSynth's wet reference; this is chiefly an effect-processing difference.** The 007 SF2 preset explicitly has two hard-left and two hard-right layers.

## Output level

P26 total signal RMS: 000 ~0.157, 007 ~0.0782 (normalized full scale).
FluidSynth *wet* RMS at gain 0.2: 000 ~0.0459, 007 ~0.0175. These levels should not be compared as an equal-gain test.

P26 007 reaches exactly 32767/32768 at ~15 sample points per channel, so a 16-bit output ceiling is reached in the initial transient. Do not assume the root cause is a generator/voice attenuation bug until compared with an independently calibrated real AWE32 output path. Adding a host output attenuation can avoid clipping, but must not silently replace the original chip's output characteristics in a hardware-fidelity mode.

## Conclusions

- **PASS:** P26 fixes the specific spurious 100-ms SF2 delay for both bass presets; CSV and waveform corroborate.
- **PASS:** 007 correct basic pitch and dry waveform shape (high correlation); 000 recognizably similar in attack.
- **NOT VERIFIED:** Matching of original AWE32 hardware wet stereo effects, exact output calibration, and all envelope stages. FluidSynth is not a valid bit-exact hardware reference.
- **Do not:** Modify 86Box chorus/reverb or chip gain solely to match the FluidSynth wet output; these are different DSP engines.
- **Next decisive evidence:** A real AWE32/AWE64 line-out capture using same bank, note, velocity, sample rate, gain and disabled/controlled external effects, or an independently validated chip-level golden trace. Tests already establish the real original ROM is being accepted; repeated ROM/SF2 path checks add little.

CI: native P26 suite 14/14 PASS, Windows VST3 build and Win32 EditorHost smoke PASS at commit fd0f28e0842dfd7f0fba5e57eeb965aad970d1ff.

