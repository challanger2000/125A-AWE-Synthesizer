# P226 – Signed32 EMU8000 preclip diagnostic

**Repository:** challanger2000/125A-AWE-Synthesizer

**Branch:** qa/p226-raw32-preclip-factorial, derived from qa/p222-controlled-fx-factorial.

**Status:** Implementation committed. Windows build, actual raw capture and original driver A/B require verified execution results. RELEASE BLOCKED.

## Measurable question

P225 established 16 P222 original-user-SoundFont VST3 Float32 captures: program 000/021, Note48/Velocity64 and Note72/Velocity120, each with GUI reverb/chorus sends DRY, REVERB, CHORUS, BOTH. MIDI CC1=96, CC7=100, CC11=127, CC91=48, CC93=32 stayed constant within groups. Four DRY cases were free of signed16 rails; five wet cases had rail samples. The exported Float32 is already limited by the EMU8000 signed16 conversion, so it does not provide actual preclip amplitude.

P226 captures the ACTUAL chip signed32 output in the real native 980-frame FIFO path, at the sample returned by Emu8000Box::RenderFrame, BEFORE Emu8000Core::RenderBlock clamps the signed32 sample to signed16.

## Implementation scope

- src/engine/Emu8000Box.h and Emu8000Box.cpp: optional, preallocated caller-owned stereo int32 tap. Disabled by default. No audio callback allocation, file I/O or locks.
- src/engine/Emu8000.h: passes opt-in raw capture through to the chip adapter.
- tools/p226_preclip_probe.cpp: actual native EMU8000 renders all 16 cases, stores signed32 PCM privately and reports raw extrema, signed16-boundary overflows, mean/RMS, first overrange frame and original signed16 rail counts. Validates every native clipped sample as exactly clamp(raw32).
- tools/p226_make_synth_fixture.cpp: reuses the synthetic P166 generator. No user media.
- tools/p226_compare_preclip_to_vst3.py: standard-library-only, strict per-sample independent comparison of clip(native raw32) against the owner-provided P222 actual-exported-VST3 Float32 WAVs. If any case differs, no VST3 parity claim.
- tools/P226-LOCAL-PRECLIP.bat: Windows owner-only package, no extra installed development tools.
- .github/workflows/p226-native-raw-preclip.yml: single Windows native CI build without downloading the VST3 SDK; synthetic ROM/SF2 only. Produces a media-free portable owner diagnostic.

## Hardware and MIDI match

- Active chip: actual 86Box-derived EMU8000, Creative Win95 driver mapping.
- Hardware FX presets: explicitly Hall 2 (4), Chorus 3 (2), matching VST3 AssetState defaults.
- NoteOn frame0, NoteOff native frame44100, 3 seconds at 44100 Hz.
- Program 000 and 021, bank0, notes 48/72 velocities 64/120, CC1=96, CC7=100, CC11=127, CC91=48, CC93=32.
- GUI sends 0 or 100 percent per FX. This is P222 test semantics, NOT proof that original Creative hardware has equivalent user controls.
- No original sample data, wave ROM, Creative driver files or user audio files in public GitHub or CI artifacts.
- No change to synth, filters, FX gains, resonance, interpolation, ROM attenuation, mastering or 16-bit output policy.

## Required evidence

| Contract | Evidence required | State |
|---|---|---|
| Raw capture truly preclip | All 264600 signed32 samples per case map exactly through clip16 to actual native int16 PCM; raw extrema not limited to signed16 | NOT RUN |
| No sonic modification by tap | Duplicate native synth rendered with and without capture, dry and strong layered wet case; bit-identical PCM | NOT RUN |
| Synthetic Windows harness | 16 actual synthetic audible chip renders, fixed CC/FX, negative sentinel, exact lengths and case counts | NOT RUN |
| Genuine original private ROM/SF2 | Run the portable executable locally against original owner assets | NOT RUN |
| Exact native and VST3 parity | Compare clip(native raw32) to 16 full-length independently recorded P222 VST3 WAVs, no amplitude normalization | NOT RUN |
| Original Win95 Creative register/audio oracle | Real owner SF2 loaded by original Creative driver, actual sample load evidence and independent original driver WAVs | NOT RUN |
| Physical AWE64 and ASIO / DAW | Original hardware capture and Studio One host audio tests | NOT RUN |
| Release | Independent complete audit and approved real-asset/host evidence | BLOCKED |

Important limitations: the native probe alone is NOT a real VST3 process tap, and signed32 output may have already saturated earlier inside a filter or FX stage. If the independent per-sample VST3 comparison fails, first investigate timing, preset, master gain and controller discrepancies rather than retuning the DSP. Raw32 clipping overrange alone does not establish physical Creative parity. No arbitrary gain normalization, DC blocker or invented send curve is authorized by this measurement.

**Local use:** Place original awe32.raw and Synth 512 Bank.sf2 alongside the portable BAT (or enter absolute paths). Running the BAT writes 16 private raw32 captures and a CSV to a new local directory and creates a private ZIP. It uploads nothing. Compare against the previously submitted P222 VST3 audio in the analysis environment; Python is not needed on the owner's computer.
