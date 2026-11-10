# Original Creative Windows 95 SF2 Volume-Sustain and Mod-Hold: 28 genuine driver observations

**Source provenance and experiment:** 2026-11-10, independently executed
original Creative SBAWE.VXD within a booted Windows 95 guest and emulated
AWE64 Gold; Windows WinMM/MIDI through real Creative driver, validated
SoundFont sample upload to original chip RAM, isolated per-note register
windows, independently executed native 125A 86Box chip register traces.

**Independent original-driver run (before the final Hold correction):**
[Private Engineering workflow #42899654680](https://github.com/challanger2000/125A-Engineering/actions/runs/42899654680),
SUCCESS. Original numeric-only artifact `Original-Creative-SF2-SustainHold-28-NUMERIC-ONLY`, ID **13803481224**.
This source is the *previously Creative-accepted public* SoundFont Spec Test v3.0
Git blob `4768c4a0215abf49c7a2bb51ada5ba3494faa1c5`.
The derived bank SHA-256 is
`e201053fd3ef4e937177803875e23ef1635e4fe5ced93a2c7c871eba67b2dfc7`.
The original six presets, 25 instrument entries, 44 samples and original
sample PCM are byte-identical. Twenty-eight distinct appended programs
100–127 are genuinely rendered and compared at note59, velocity100.

**Result BEFORE repairing generalized Mod Hold:**
- SF2 generator 37 (`SustainVolEnv`): **14/14 independently measured Creative
  chip-register upper bytes match** current Win95 integer mapping, including
  960→6 and the value boundary 1000/1440→0.
- SF2 generator 27 (`HoldModEnv`): **11/14** match the then-current simplified
  `round(ms/92)` implementation. The three actual original-driver failures:
  input timecents -2400 native124 vs original125, -600 native119 vs
  original120, +1200 native105 vs original104. They were NOT patch-specific.
- The original 28-case comparison completed SUCCESS **as a measurement run**,
  but 3 mismatches are real and must not be labelled a parity PASS.

| SF2 HoldModEnv tc | REAL original Win95 Creative ATKHLD high | Former ms-round native | Correct VXD-quantized integer candidate |
|---:|---:|---:|---:|
| -12000 | 127 | 127 | 127 |
| -6000 | 127 | 127 | 127 |
| -3600 | 126 | 126 | 126 |
| -2400 | 125 | 124 | 125 |
| -1200 | 122 | 122 | 122 |
| -600 | 120 | 119 | 120 |
| -120 | 117 | 117 | 117 |
| -1 | 116 | 116 | 116 |
| 0 | 116 | 116 | 116 |
| 1 | 116 | 116 | 116 |
| 100 | 115 | 115 | 115 |
| 300 | 114 | 114 | 114 |
| 600 | 112 | 112 | 112 |
| 1200 | 104 | 105 | 104 |

Additional 14 Creative generator37 upper-byte observations,
input (centibels): output:
0→127, 1→127, 10→126, 64→119, 127→111,
250→96, 500→64, 750→32, 959→6, 960→6,
961→5, 999→1, 1000→0, 1440→0.

## Root cause and general correction

The old simple SF2 timecents→continuous milliseconds→nearest 92ms formula
**does not** implement original Creative's integer arithmetic. The original
VXD translates SF2 timecents to an integer **725-microsecond delay-unit
register first** using the documented discrete, within-octave fixed-point
approximation `DelayFromTimecents(tc)`. It then truncates the delay count
to 92ms hardware Hold units by the integer formula:

```cpp
int tc = clamp(originalHoldTc + (60-note)*keyHoldScale, -12000, 5484);
int delayTicks = 0x8000 - DelayFromTimecents(tc);
int steps = int(int64_t(delayTicks) * 725 / 92000);
return clamp(127-steps, 0, 127);
```

This algorithm **already existed** in a P208 test-only 125A native candidate
behind `AWE125_P208_SF2_HOLD_SUSTAIN`; the historically authenticated
[original Creative P210 14-case trial #42722686808](https://github.com/challanger2000/125A-Engineering/actions/runs/42722686808)
measured **14/14 native Hold candidates identical** to real Win95 Creative
registers, including tc+2400→81. The newer 28-case actual original observations
independently establish 14 further Hold scenarios (many overlapping, but
additional boundary points); the same VXD-quantized integer algorithm predicts
**14/14** for this series as well.

The final actual source now implements the P208 proven route **only for SF2 /
Win95 / Modulation Hold**, with `int64_t` key scaling and saturating
timecents limits. It does NOT change SF1, DOS, volume-hold, FX, original
sample playback or chip DSP. `tests/creative_win95_sf2_envelope.cpp` freezes
all 28 independent Creative measured values and includes explicit negative
witnesses for the incorrect old 92ms rounding.

## Post-correction validation and remaining gates

- Native Linux original-register-anchored regression:
  [CI #42903894962](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42903894962)
  SUCCESS, 4/4 selected CTests; 28 frozen independent real-driver
  input→register vectors all match. This is native C++ parity against
  authenticated original numerical evidence, not fresh driver playback.
- Full **fresh original Creative Win95 28-note rerun with current corrected
  chip**: [private workflow #42904061108](https://github.com/challanger2000/125A-Engineering/actions/runs/42904061108),
  **PENDING** at initial drafting; do not claim it succeeded until job
  concludes and 28/28 original register observations are read.
- Actual exported **Win64 VST3** targeted host PCM after correction:
  [Windows workflow #42903971457](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42903971457),
  **PENDING** at initial drafting; no real Studio One / ASIO qualification.
- Full owner 77/376 preset original-driver acoustic PCM comparison, physical
  AWE64 hardware comparison, clipping fidelity and Studio One release gates
  remain **NOT RUN / NOT PROVEN**. The previous 117 dry clipping cases
  are **NOT claimed fixed** by the register-only change.
- No private owner SF2/ROM/Win95 binaries are uploaded into the public
  product repository or packaged artifact; original guest material remains
  private. No merge to main and NO RELEASE.
