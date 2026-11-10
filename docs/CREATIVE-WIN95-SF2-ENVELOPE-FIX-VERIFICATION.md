# Original Creative Win95 SF2 envelope parity — verified correction, 2026-11-10

## Actual user-bank problem, real independent oracle

The real original **Creative SBAWE.VXD in Windows 95** was run in the private
86Box guest using a verified **two-presets-derived subset** of the owner's
`Synth 512 Bank.sf2`. The same original sample bank and MIDI note/program
were played via the current native 125A EMU8000 core. This test is **not**
generated from a guessed register oracle. Private user SF2 bytes, ROM,
Windows guest and WAVs were **never uploaded into the public product repo**.

Exact test: bank0, program7 **TX81Z Lately Bass**, note99, velocity112.
Original before correction (real driver vs current engine):
- all four `ATKHLD` high bytes: original `0x74`, native `0x75`
- all four `DCYSUSV` program-note start high bytes: original `0x06`,
  native `0x00`; low decay-rate bytes and prior/release writes matched
- the remaining four `CSL_HI` differences were the deliberate 125A GUI
  **Chorus 0%**, not a mismatched instrument parameter.

Original prior independent Creative comparison:
[private run #42812968124](https://github.com/challanger2000/125A-Engineering/actions/runs/42812968124)
is **SUCCESS**, establishes the baseline **116/128 exact P007 register
write histories (8 non-FX mismatches)** and P000 **60/64 (FX only)**.

## Narrow production DSP correction

**Source: `src/engine/SoundFont.cpp`, no DSP chip, effects, SF2 parser,
ROM, MIDI, GUI or parameter ID changes.**

1. For **SF2 + Win95 only**, map explicit `SustainVolEnv` using an
   integer 0..1000 conversion `127 + (-127 * clampedValue)/1000`.
   This gives the actual original `960 -> 6`; before the patch an
   unrelated 0.75-dB approximation clipped it to zero. The absent
   generator retains full sustain (127).
2. For **SF2 + Win95 modulation-envelope Hold only**, round the
   nonnegative millisecond hold duration to the nearest 92ms register step
   rather than DOS `idiv` truncation. Original `0` timecents =
   `1000 ms` now maps to register `0x74` (116), rather than `0x75`
   (117). The already-matching VolumeEnvelope Hold path remains
   untouched, as do DOS and SF1 conversions.

The actual original Creative run proves **those exact owner-source input
vectors**. Other generator values and every boundary have not yet been
swept through the original driver, so these generalized formulas must
remain a controlled, regression-tested candidate outside that anchor.

## Executed proof AFTER the patch

- **Real original Creative-driver retest: SUCCESS**
  [private GitHub Actions #42891309497](https://github.com/challanger2000/125A-Engineering/actions/runs/42891309497),
  original AWE64 Gold PnP, original Wave ROM, Windows 95 Creative driver,
  original SoundFont upload, real wavetable PCM and actual independent
  EMU8000 port-write trace verified.
- **Grungy Ramp Bass** (original program0), note99 velocity112:
  **60/64 exact**, with all 4 mismatches being intentional FX sends;
  **no non-FX register differences**.
- **TX81Z Lately Bass** (original program7), note99 velocity112:
  **124/128 exact**, with all 4 mismatches being intentional FX sends;
  **no non-FX register differences**. Both prior `ATKHLD` and
  `DCYSUSV` mismatches are eliminated across all four real chip
  voices, while the channel register histories match.
- **Real exported Windows x64 VST3**:
  [Windows Actions #42893233535](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42893233535)
  **SUCCESS**, Steinberg SDK pinned v3.8.1 build84, 47/47
  automatically executed Steinberg SDK validation, 2/2 targeted
  Windows CTests, and actual exported instrument hosted in the
  existing P220 independent AudioProcessor with a generated SF2,
  producing two PCM16 WAVs; the dry PCM was validated **nonzero**.
  Original private user SF2 was **NOT** loaded in this public Windows
  host test. A test-workflow-only `-D125A_BUILD_OPL3_PROBES=OFF` had
  broken linking of the existing `awe32_opl3_midi` target; that test
  configuration is now corrected. Production `src/vst3/CMakeLists.txt`
  is unchanged from the reference parent branch.
- **Four real owner SF2 sound banks / 376 presets**:
  **3,082/3,082 real 86Box-derived native EMU8000 dry audio note renders**,
  each 2s/44.1kHz/stereo. **0 silent cases, 0 active-voice FX register
  leakages, 0 signed32-to-int16 clipping-model mismatches.**
  The **234/234** previously measured P229 dry/velocity controls have
  *identical* audio stats after the register correction.
  The **117 prior dry overrange cases remain 117**. This fix is a
  **register parity fix, NOT a measured audio clipping fix**.
  The dry returns are 0 by user's explicit project requirement,
  even when the original SF2 had nonzero FX generators.

## Scope and release status

- **Confirmed:** exact instrument register-write histories for two
  original owner-derived presets on note99/velocity112, excluding
  deliberate effects 0; targeted native and actual Windows VST3 build.
- **Not proven:** full SoundFont original-driver playback for all 77
  original presets or all 376 presets across four banks; acoustically
  sample-exact Creative-vs-native PCM, calibrated original Creative
  wavetable gain and note-off/FX matching; physical CT4390/AWE64;
  Studio One user DAW/ASIO acceptance; all-state/recall and all
  VST3/Plugin Test Lab release QA gates.
- Creative WAV recorder and local VST3 native WAV are **different
  duration/trigger/mixer/FX operating conditions** and cannot be
  used as unqualified level parity. No gain/limiter/DC adjustment was
  introduced on the basis of their difference.
- **Research candidate only. No main merge, no release, no release QA PASS.**
