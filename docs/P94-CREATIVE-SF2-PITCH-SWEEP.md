# P94 – Original Creative Windows 95 SF2 pitch sweep (verified)

## Evidence

Original driver and AWE64 Gold in 86Box, note-on register trace. Private test: https://github.com/challanger2000/125A-Engineering/actions/runs/41707731016 (SUCCESS, 30/30). Original private SF2 not published. P92 source commit `0404bc643974623db145714ad054dbd48407f796`. The isolated P92 note-48 comparison still yields **63/64 matching register-write series** and **94/94 identical note register-write counts**.

The P94 test extended the original program-0 bank MIDI notes from 48 to **45–56, 60, 61**. For those notes two instrument regions are active, with the original SF2's `overridingRootKey=45`, `coarseTune=-12`, `fineTune=+5/-5`, sampleRate 44100 Hz, sample root 60, and sample correction 0. Reference pitch was computed using the current original-VXD-derived `PitchFromCents` integer routine, at effective cents `(note-45)*100-1200+fineTune`.

| MIDI | Creative +5 | Native formula +5 | Creative −5 | Native formula −5 |
|---:|---:|---:|---:|---:|
| 45 | D010 | D011 | CFEE | CFEE |
| 46 | D165 | D166 | D143 | D144 |
| 47 | D2BB | D2BB | D298 | D299 |
| 48 | D410 | D411 | D3EE | D3EE |
| 49 | D565 | D566 | D543 | D544 |
| 50 | D6BB | D6BB | D699 | D699 |
| 51 | D810 | D811 | D7EE | D7EE |
| 52 | D966 | D966 | D943 | D944 |
| 53 | DABB | DABB | DA99 | DA99 |
| 54 | DC10 | DC11 | DBEE | DBEE |
| 55 | DD66 | DD66 | DD44 | DD44 |
| 56 | DEBB | DEBB | DE99 | DE99 |
| 60 | E411 | E411 | E3EF | E3EE |
| 61 | E566 | E566 | E544 | E544 |

**28 original voice IP writes: 17 exact, 10 original one unit lower, 1 original one unit higher.** All data refer to the original driver's IP port writes and this source's existing mathematical conversion. They are *not* an independent broad 28-voice native executable re-run. MIDI note 72 used a different sample region and is excluded from this comparison.

## Interpretation and release gate

A constant one-unit correction is demonstrably invalid: it would break the 17 already-matching examples. Differences may arise from the driver-specific construction of SF2 sample pitch, tuning components, or fixed-point rounding. The exact intermediate guest pitch arithmetic is still unproven; P93 attempted a specific VXD helper address and observed zero calls, while the actual EMU8000 IP port and CPU call stacks were captured successfully in https://github.com/challanger2000/125A-Engineering/actions/runs/41700349731. **Do not conflate successful diagnostic/CI runs with proven full 1:1 hardware or acoustic parity.**

Do not change the production Win95 SF2 pitch formula until a general rule is justified by original Creative arithmetic and verified against all P94 notes and the P92 full 64-series register regression. Existing successful P92 VST3 remains the reference.
