# Actual original Creative Windows 95 driver direct A/B: owner basses, 2026-11-10

**This is executed original-driver evidence**, not a synthetic expected-value test.
Private Engineering GitHub Actions: https://github.com/challanger2000/125A-Engineering/actions/runs/42812968124 (**SUCCESS**).
Source and 86Box original emulated AWE64 Gold with 28 MiB, actual Windows 95,
Creative SBAWE.VXD, WinMM AWE Synth and Creative AWECP SoundFont sample upload;
P67 guest log and the EMU8000 wavetable output both independently verified.
The source was the private, SHA-256-verified **two-original-preset subset**
of the user's Synth 512 Bank SF2, **not the entire 77-preset SoundFont**.
Only numerical evidence is archived privately; no guest, ROM, SF2 or WAV
media was published in GitHub.

**MIDI:** original Creative user CC0 bank 1, program 0/7 corresponding
to original SF2 bank 0, note 99, velocity 112, Win95 driver mapping.
Both original Win95 captured notes and the current native chip used the
*same underlying two-preset source SF2*. They **did not** have the same
FX sends or note-off timings, and the 86Box original wavetable recorder and
native output have not been calibrated to the same mixer/gain point.

## Actual register-history result

| SF2 preset | Source Win95 active voices | Native active voices | Complete register series equal | Differ |
|---|---:|---:|---:|---:|
| P000 Grungy Ramp Bass | 2 | 2 | **60 / 64** | 4 intentional FX sends |
| P007 TX81Z Lately Bass | 4 | 4 | **116 / 128** | 4 chorus sends, 4 ATKHLD, 4 DCYSUSV |

For P000 all FOUR mismatches are exclusively original wet FX versus explicit
125A GUI 0%:
- each voice **CSL_HI** Creative `0x7F20`, native `0x0020`.
- each voice second **PTRX_LO** Creative `0x0581`, native `0x0081`.
All filter, sample-address, pitch, envelope, attenuation and other register
**write histories** match. This is *register parity*, NOT acoustic identity.

For P007 the four chorus mismatches are also intentional 0%:
- per voice **CSL_HI**: original `0x6620` / `0x4C20`, native `0x0020`.
The eight **genuine instrument mismatches** are:
- **ATKHLD** in each of four voices: original `0x740C`, native `0x750C`;
  one high-byte Hold step. Actual user's SF2 region has raw HoldModEnv=0tc.
- **DCYSUSV** in each of four voices: original **`0x061D` /
  `0x0633`**, native **`0x001D` / `0x0033`** at note start.
  The leading `0x00FF` and release `0x801D` / `0x8033` writes
  remain equal, so this is not a program/voice identity mismatch.
  The private original P007 SF2 preset zones explicitly contain
  `SustainVolEnv` generator 37 = **960 centibels**. The current
  `SoundFont.cpp` maps 960cb through a 0.75 dB chip step, clipped to 0;
  the actual original Win95 Creative driver writes 6. A promising
  **hypothesis**, NOT an approved generic fix, is the existing Creative
  integer percentage-style conversion used for ModEnv, because
  `127 + (-127*960)/1000 == 6` in C++ integer truncation.
  The full genuine SustainVolEnv sweep/driver routine must confirm this
  for other values/boundaries and preset+instrument additive layers.
  DO NOT hardcode 6 or patch one particular bass.

## Observed WAVs, not yet calibrated A/B

Both are 44,100 Hz, stereo, PCM16, and non-silent in both executions.

| User preset | Original Win95 Creative wavetable (118638 frames) | Current native 125A chip (88200 frames) |
|---|---|---|
| P000 note99/V112 | peak 6,223 counts, 0 rails; RMS -36.40 dBFS | peak 19,858 counts, 0 rails; RMS -30.53 dBFS |
| P007 note99/V112 | peak 9,598 counts, 0 rails; RMS -35.40 dBFS | peak 32,768 counts, **312 rails**; RMS -20.13 dBFS |

This does **not** establish the original EMU8000 internal signed32 preclip
peak. The original recording has additional mixer gain, nonzero preset
chorus and a 1.2s note-on+1.2s note-off duration, versus the native
2.0s note-on recording. Original first-nonzero frames ≈5,542/5,557;
native ≈994/1,001. Waveforms/absolute RMS **cannot** be called 1:1
or corrected by guessed global gain. The 312 rails reproduce the
previous native P228/P229 P007 clipping finding.

## Concrete next correction gate, WITHOUT another broad audit

1. Extract or corroborate the **original Creative Win95 SF2 generator-37
   SustainVolEnv conversion** for values around 0, 500, 960, 1000 and
   instrument+additive-preset combinations. This is the high-impact
   P007 `DCYSUSV` discrepancy. Preserve SF1 and DOS branches.
2. Establish the original Win95 **SF2 HoldModEnv** timecents-to-ATKHLD
   integer conversion. P007 raw timecents0 yields original 116,
   current native 117. Preserve instrument/preset key scaling.
3. Verify fixes against independent original Win95 reference traces
   and existing SF1/SF2 regression tests. Audio core and gain must
   **not** be modified merely to make the recorded peaks equal.
4. To generalize across all user banks, use actual original SF2 source
   and matching MIDI events and a calibrated 86Box wavetable capture.
   The current successful original driver test covers **two source presets
   only**, not all 376, not physical AWE64 hardware, not VST3/Studio One.

**Status: ORIGINAL CREATIVE WIN95 REAL DRIVER A/B EXECUTED AND PASS FOR
PROVENANCE; P000 instrument register parity PASS; P007 instrument register
parity FAIL (8 non-FX histories); full audio/hardware parity OPEN;
production DSP unchanged; NO release/merge.**
