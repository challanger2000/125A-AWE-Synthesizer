# P213 research sources – stop guessing Creative EG1 Sustain arithmetic

Research/source inventory only. **No DSP patch, no firmware/driver upload, no new formula asserted.**

## Authentic original source hierarchy

1. **Actual tested Creative Win95 binaries, not the older SDK example:** P212 original-driver workflow https://github.com/challanger2000/125A-Engineering/actions/runs/42727927825 retrieved from the pinned historical driver-mirror directory `https://sobac.com/ZIPfiles/Operating%20Systems/Windows/Drivers/Audio/SB16%20CT2940/`. Source is documented in `tools/p38_stage_creative_awe32_win95.py`. The original staging log records:
   - `SBAWE.VXD`, 77,370 bytes, SHA-256 `d343f2428ab3e593c9e42a668cf521b7801e1239792eaf7f2b11b5f179bc7c9a`.
   - `SBAWE32.DRV`, 45,264 bytes, SHA-256 `bb15f48760f197122e2e1d88f251d57681496e1d8188213e250c3b7fead7963c`.
   - Both were installed in a transient original Windows 95 guest and the original Creative WinMM endpoint was exercised. These exact versions, not similar-named packages, are the target for binary analysis. Do not upload proprietary binaries or guest images.
2. **Official original chip manual**, E-mu/Creative 1994–1996, *AWE32/EMU8000 Programmer's Guide*, rev 1.00, original printed p.16, DCYSUS: https://www.dosdays.co.uk/media/creative/emu8kpgm.pdf . Bits 14..8 encode the 7-bit mod-envelope sustain level; 0x7f full/no attenuation, zero off. Bit 15 indicates decay vs release; low seven bits are decay/release time. This manual DOES NOT document how the Win95 SF2 parser rounds 0..1000 to DCYSUS.
3. **Official SoundFont 2 technical specification**, `sustainModEnv` generator opcode 29, original printed p.33: https://www.synthfont.com/sfspec24.pdf . Units 0.1 percent decrease; 0 = full and 1000 = zero; clamp outside range. It does NOT mandate the historical Creative/Windows driver's precise integer rounding.
4. **Actual independent source code**, Takashi Iwai AWEsfx Linux SF2 loader: https://github.com/tiwai/awesfx/blob/master/awelib/awe_parm.c , functions `calc_mod_sustain_adip`, `calc_mod_sustain_trad` and `awe_calc_mod_sustain`. SF2-to-register wiring: https://github.com/tiwai/awesfx/blob/master/awelib/parsesf.c , `set_modenv`. The ADIP formula subtracts an integer-scaled 127 fraction, and traditional mode uses a different mapping. Neither is the original 1998 Creative Win95 binary. Compare as alternatives; NEVER label either the Creative oracle or import it without evidence/license review.
5. **Original archived Creative SDK (earlier revision)**: https://github.com/qb40/sound-blaster-awe32 . Its `WINDOWS/DRV/WIN95/SBAWE.VXD` is 85,918 bytes whereas the original driver actually tested in P212 is 77,370 bytes. Do not silently assume same driver revision or identical SF2 conversion code.

## Empirical source: P212 observations and falsification

Original-driver evidence: https://github.com/challanger2000/125A-Engineering/actions/runs/42727927825 ; artifact `P212-Creative-Win95-EG1-28Program-Sustain-Register-Oracle`, authentic Creative Windows 95 SBAWE.VXD through WinMM in 86Box AWE64 Gold with 28 MiB; not physical hardware. Source SHA is in the artifact manifest. New note tests at 59/velocity100; 24 unseen Sustain generator values, 4 independent repeat controls.

The P211 `127 - ties_to_even(126 * sustain / 1000)` hypothesis fails six measured points:

| SF2 decrease | actual original DCYSUS high byte | predicted P211 |
| ---: | ---: | ---: |
| 249 | 0x5F | 0x60 |
| 375 | 0x4F | 0x50 |
| 376 | 0x4F | 0x50 |
| 624 | 0x31 | 0x30 |
| 625 | 0x31 | 0x30 |
| 751 | 0x21 | 0x20 |

Scores 22/28 total; 18/24 unseen values; full details and unchanged raw integer observations in P212 artifact. Genuine original driver audit SUCCESS means evidence acquisition PASS only; prediction FAIL.

## The required next investigation: source-directed, not statistical guess

1. **Provenance-first static analysis** of the exact matching 1998 Creative `SBAWE.VXD` and `SBAWE32.DRV` in a temporary private CI workspace; verify SHA-256 before disassembly. Determine which module actually transforms `sustainModEnv` into the per-voice sustain byte. Inspect possible table lookups, signed arithmetic, fixed-point steps, and any intermediate generator inheritance. Do not claim a formula until a concrete instruction path or table reproduces trace values. Do not publish original proprietary code or binaries; write down offsets, short algorithmic summaries and derived tables where justified.
2. Freeze all P210 and P212 observed numeric values as immutable source-oracle fixtures. Any proposed formula must reproduce both sets without rewriting them.
3. For remaining ambiguity, add **targeted new original Creative guest measurements** only where static analysis requires them (e.g. table boundary, rounding branch, interpolation branch). Stop wasteful rebuilds without a falsifiable hypothesis.
4. Distinguish three gates: exact version original Win95 driver register behaviour, any real physical EMU8000 hardware output, and the DAW/VST3 product path. Unrun gates remain NOT RUN.
5. No product DSP changes, merge, FULL AUDIT or release approval until source hypothesis is actually verified.

**Research status:** authoritative semantic and register sources found; tested 1998 Creative binary identified and hashed; source-level conversion routine still **NOT DECOMPILED / NOT PROVEN**. P211 is falsified. Product remains unchanged.
