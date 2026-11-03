# P92 – original Creative VXD SF2 fixed-point conversion batch

## Verified source evidence

The original Windows 95 Creative `SBAWE.VXD` binary was downloaded into a **transient private GitHub runner**, validated as a Windows VXD, and only narrow machine-code conversion branches were disassembled. No vendor binaries, proprietary sample data, or user SoundFont were published.

- Actual private soundbank scalar extraction for **program 0, note 48, velocity 100**: `freqModLFO=-617`, `attackVolEnv=-8828`, `freqVibLFO` absent (SF2 default 0). Source `P92-SF2-Generator-Scalars-PRIVATE`, private diagnostic workflow `https://github.com/challanger2000/125A-Engineering/actions/runs/41556904779`.
- Creative VXD SF2 conversion branch `C119C180` (original file approximately offset `0xFE62`) handles *both* LFO frequencies in 16.16 fixed point. Addition of `0x23A6` (9126), integer division by 1200, 16-bit fractional linear interpolation and saturation to `0xFF`; `-16000` cents and below return zero. `-617 -> 0x8B` and `0 -> 0xCD` — precisely the original P91 trace.
- Creative VXD SF2 attack branch `C119C1D9` handles *both* volume and modulation attacks directly in timecents: `tc <= -600: min(128, (37-tc)/75+8)`; `tc >= 4300: 1`; middle region uses the driver’s bit-shift mantissa transformation. `-8828 -> 0x7E`; `-1200 -> 0x18`. The prior millisecond attack lookup was appropriate for SF1 but not original Win95 SF2 conversion.
- The narrow disassembly is saved in the private `P92-Original-Win95-Converter-Disassembly-PRIVATE` artifact of `https://github.com/challanger2000/125A-Engineering/actions/runs/41557335811`.

## Changes

The Win95 SF2 branch now uses two common original Creative conversion functions for both LFOs and both envelopes. SF1 and DOS/SDK paths are intentionally unchanged. `tests/p90_sf2_driver_registers.cpp` adds multiple disassembly-derived test vectors, the measured real original bank inputs, edge clamps and DOS backward-compatibility cases. All modifications share **one commit and one Windows VST3 CI trigger**; do not build per register.

## Pending verification

Original Creative P91 baseline is 57/64 equal series and 94/94 write counts. P92 targets the *six* mismatches in `TREMFRQ`, `FM2FRQ2`, `ATKHLDV`. The seventh, **IP pitch** of the first voice (`0xD410` original versus `0xD411` native) is **not automatically changed**: the independently disassembled `PitchFromCents` converter already matches Creative, so the one-unit discrepancy requires an upstream generator/pitch-composition trace and not a per-preset hack. Repeat the actual Creative Win95 driver trace before claiming the six register series repaired.

No hardware acoustic or physical-board 1:1 conclusion follows from register matching.
