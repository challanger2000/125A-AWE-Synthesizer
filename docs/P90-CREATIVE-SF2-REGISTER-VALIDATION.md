# P90 – Win95 Creative SF2→EMU8000 conversion corrections

**Status:** P90 native C++ tests PASS and Windows VST3 build PASS; repeat original Creative Win95 trace run is pending. Not yet a final 1:1 hardware claim.

## Reproducible baseline

The genuinely executed original Creative Windows 95 MIDI driver on a simulated AWE64 Gold (28 MiB) gave 21 mismatching native register histories across 64 inspected series for the private SF2's bank 0 / program 0 (Grungy Ramp Bass), MIDI note 48, velocity 100. Private [P89 original-driver run](https://github.com/challanger2000/125A-Engineering/actions/runs/41542902713).

The reduced test SF2 and full `Synth 512 Bank.sf2` generated bit-identical native PCM for this same program. The private SF2 itself and sample-memory trace are not included in this public repository.

## Corrections implemented (generic Win95 SF2 branch, not specific instrument names)

| Register family | Original Creative | P89 native | P90 native after fix | Status |
|---|---|---|---|---|
| CCCA filter Q (high) | `0x8020` | `0x6020` | `0x8020` | matching measured value |
| CCCA sample-start (low) | `0x05B8` | `0x05B7` | `0x05B8` | matching measured value |
| PSST loop-start first write | `0x05C4` | `0x05C3` | `0x05C4` | first write matching |
| CSL loop-end first write | `0x0755` | `0x0754` | `0x0755` | first write matching |
| CSL chorus-send (high) | `0x7F20` | `0x8020` | `0x7F20` | measured value matches, **extra native write** pending |
| TREMFRQ depth high | `0x15` | `0x2A` | `0x15` | measured depth matches; frequency byte pending |

Original Creative Win95 `initialFilterQ=100` centibels yielded EMU8000 Q8. The current Win95-SF2 conversion uses 12.5 cB per Q unit. **Other Q magnitudes require additional independent Creative examples** before this mapping can be considered universally validated. The native change is intentionally Win95-specific; DOS/SDK pathways are preserved.

Other uncorrected discrepancies include ATKHLDV attack `0x7E` vs `0x7D`, IP pitch `0xD410` vs `0xD411`, FM2FRQ2 frequency `0xCD` vs `0xC3`, TREMFRQ frequency `0x8B` vs `0x88`, and extra PSST/CSL/DCYSUSV writes around release. We do **not** hardcode adjustments for this single bass.

## Tests

- Synthetic C++ SF2 register conversion checks for Win95 and unchanged DOS pathways: `tests/p90_sf2_driver_registers.cpp`.
- Native 86Box/EMU8000 SF2 integration with generated 24.68 MiB sample data: [P90 native CI](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41546829570), **SUCCESS**.
- Windows x64 VST3 CI on the updated sound engine: [P90 Windows CI](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41546554602), **SUCCESS**.
- Original Creative full-register repeat: [P90 private CI](https://github.com/challanger2000/125A-Engineering/actions/runs/41546374534), status pending at time of this note.

**Important:** Matching a few measured register words does not prove complete musical, acoustic, or physical AWE64 identity. Native P90 audio was confirmed to render nonzero PCM; the audible high-frequency discrepancy is not yet resolved.
