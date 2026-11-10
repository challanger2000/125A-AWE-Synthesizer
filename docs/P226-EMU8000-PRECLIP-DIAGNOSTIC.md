# P226 – Signed32 EMU8000 preclip diagnostic

**Repository:** challanger2000/125A-AWE-Synthesizer

**Branch:** qa/p226-raw32-preclip-factorial, derived from qa/p222-controlled-fx-factorial.

**Status:** Windows-native P226 synthetic CI SUCCESS (Actions #42787336357, source 5b3dc35e). Owner-provided P226 private 16-case real-bank raw32 ZIP independently evaluated against previously submitted genuine P222 real-exported-VST3 Float32 recordings: **4,233,600/4,233,600 audio values bit-identical after actual signed16 clamp; 5/16 cases with preclip overflows**. Original Creative driver A/B remains NOT RUN. RELEASE BLOCKED.

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
| Raw capture before clamp (synthetic + owner media) | All 264600 native signed32 samples per case map through clip16 to native int16 PCM; original P222 F32 values match all cases | PASS: Windows #42787336357 + owner original media P226 actual raw32 A/B; 5 overrange cases |
| No sonic modification by tap | Duplicate native synth rendered with and without capture, dry and strong layered wet case; bit-identical PCM | PASS: Windows #42787336357, two synthetic cases |
| Synthetic Windows harness | 16 actual synthetic audible chip renders, fixed CC/FX, negative sentinel, exact lengths and case counts | PASS: Windows #42787336357 |
| Genuine original private ROM/SF2 | Run the portable executable locally against original owner assets | PASS: owner P226 private 16-case raw32 capture; does NOT prove Creative Win95 driver original bank loading |
| Exact native and VST3 parity | Compare clip(native raw32) to 16 full-length independently recorded P222 VST3 WAVs, no amplitude normalization | PASS: 4,233,600 / 4,233,600 bit-identical, 0 mismatches; 4 adversarial mutations detected |
| Original Win95 Creative register/audio oracle | Real owner SF2 loaded by original Creative driver, actual sample load evidence and independent original driver WAVs | NOT RUN |
| Physical AWE64 and ASIO / DAW | Original hardware capture and Studio One host audio tests | NOT RUN |
| Release | Independent complete audit and approved real-asset/host evidence | BLOCKED |

Important limitations: the native probe alone is NOT a real VST3 process tap, and signed32 output may have already saturated earlier inside a filter or FX stage. If the independent per-sample VST3 comparison fails, first investigate timing, preset, master gain and controller discrepancies rather than retuning the DSP. Raw32 clipping overrange alone does not establish physical Creative parity. No arbitrary gain normalization, DC blocker or invented send curve is authorized by this measurement.

**Local use:** Place original awe32.raw and Synth 512 Bank.sf2 alongside the portable BAT (or enter absolute paths). Running the BAT writes 16 private raw32 captures and a CSV to a new local directory and creates a private ZIP. It uploads nothing. Compare against the previously submitted P222 VST3 audio in the analysis environment; Python is not needed on the owner's computer.


## Executed evidence (2026-11-10)

- [Windows Actions #42787336357](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42787336357) **SUCCESS**, confirmed through job step results and actual artifacts; source commit 5b3dc35edc5970ef565da02bfe8bef5753b9ed17.
- 16 actual native EMU8000 captures, 132300 stereo frames per case; all 16 synthetic chip outputs remained inside signed16 range, so this run does NOT reproduce owner's clipping.
- Full native int32->int16 exact mapping for each of 264600 samples per case, plus two native capture-enabled versus capture-disabled PCM equality checks: **PASS**.
- C++ signed16-saturation test-only negative mutant and Python comparator mutation: **PASS**.
- Portable media-free owner test ZIP: GitHub artifact ID 13749838688, Windows EXE SHA256 A25F7FBB81F52622F9B4B519B3C41823468531F29EF65CEA899180ABC32786ED.
- Real user original ROM and 77-program SF2, the prior 16 P222 VST3 WAV comparisons, original Win95 Creative driver and physical AWE64: **NOT RUN** by this Windows CI.

## Verified owner-private native preclip measurement (2026-11-10)

Owner's uploaded `P226-PRIVATE-20261110-101049.zip` SHA256
`a6fdccfdbbf7d1d31f4c4735f833a048dd42a09061ee59e0ab624bed7bda9227`.
Prior P222 real-exported-VST3 F32 capture archive SHA256
`d7604dfbce99aef1217832b3f8409bc643b9ceb21e515cd857e9bf2741306196`.
Both retained privately; **neither uploaded or committed to GitHub**.

- 16/16 complete 132,300-frame 44,100 Hz stereo signed32 captures, 4,233,600 samples total; P226 CSV values independently reproduced from the raw files.
- Exact sample-by-sample equality of `clip16(P226 signed32) / 32768` and P222 VST3 Float32 output: **4,233,600/4,233,600 equal, zero mismatches**. Audio reaches the native signed16 rails in five cases.
- **True signed32 preclip overrange:** P000 N72/V120 CHORUS 1,378 values (peak +3.69 dBFS); P000 N72/V120 BOTH 1,486 (+4.16 dBFS); P021 N72/V120 REVERB 8,751 (+4.27 dBFS); P021 N72/V120 CHORUS 9,388 (+5.31 dBFS); P021 N72/V120 BOTH **46,482** (+7.80 dBFS, −80,405 integer minimum, 17.57% of the 264,600 values). All four dry cases had zero overrange.
- Each of the four program/note-velocity quartets satisfies `BOTH - REVERB - CHORUS + DRY` with **max absolute integer residual 2** and RMS error under 0.765 integer counts. Effect returns therefore add almost exactly **before** the 16-bit clip; this is *not* evidence that the original physical Creative DSP uses identical effect return gain or send law.
- Four independent, executed negative mutations rejected correctly: single F32-grid LSB error, one-frame time shift, stereo L/R swap and truncated native int32 capture. Test was run on real original-bank 16-case outputs, not merely synthetic CI fixtures.
- Evidence status is **measured 125A software EMU8000**, not a physical AWE64 reference, and the 100% sends correspond to direct hardware maximum register values (255), not an independently observed original-driver intended performance level. Do NOT apply an arbitrary post-mixer gain, DC highpass, peak limiter or send taper as a sound-fidelity correction on this evidence alone.

**Next real parity gate:** original Win95 Creative driver must actually load this bank, issue the same note/velocity/CC/FX preset instructions and produce observable register sends + audio so internal FX return levels can be judged against the historical reference. Physical AWE64 and Studio One/ASIO acceptance remain NOT RUN; release NO-GO.
