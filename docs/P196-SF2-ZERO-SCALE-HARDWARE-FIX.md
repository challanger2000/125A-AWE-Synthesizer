# P196 — SoundFont scaleTuning=0: correct fixed-pitch key-number envelopes

Date: 2026-11-09. Product branch `fix/p190-zero-fx-dry`. Target: only SF2/Win95 explicit `scaleTuning=0`; do not change any P190 FX, FX sends/returns, ROM, audio core, GUI or state.

## Reproduced physical-reference discrepancy

The independent CT4390 AWE64 Gold real analog 264s reference used the original SHA-pinned [SoundFont Specification Test v3](https://github.com/mrbumpy409/SoundFont-Spec-Test). The previous P193 dry/wet-matched native 86Box experiment had 50–200Hz excess +2.848dB after a single global level match. P194 measured 93.37% of the *signed net excess* from section 04 keynum-to-hold, and 14.96% from section 03 keynum-to-decay (other sections offset the sum). P195 identified incorrectly pitched native low C3 131Hz and C2 65Hz from MIDI notes 48 and 36 in those sections.

P196 read-only RIFF SF2 generator parser independently verified original public instrument generator values (not inferred from product code):
- Program 1 `keynum-to-decay`: `keynumToVolEnvDecay=101`, `scaleTuning=0`, sampleID 43.
- Program 2 `keynum-to-hold`: `keynumToVolEnvHold=101`, `scaleTuning=0`, sampleID 43.

With `scaleTuning=0`, the key number changes the volume envelope's hold/decay, **not** sample pitch. The prior converter in `SoundFont::MakeVoiceParams` always used `(key-rootKey)*100` cents, except for a historical `scaleTuning==1` half-step. Consequently, C2/C3 notes incorrectly produced 65/131Hz rather than the original sample's fixed pitch.

## Exact correction

For **explicit `scaleTuning=0` in SF2 Win95 only**, set `pitchCents=cents` (sample correction and coarse/fine tuning retained), independent of note number. All absent/default `scaleTuning=100`, other nonzero settings, SF1/SBK and DOS driver conversion remain unchanged. This minimal path is intentionally narrower than a speculative full 0–1200 scaleTuning remapping. Existing independently measured P96 creative pitch-register vectors must continue passing.

A new always-active Release-safe regression in `tests/p90_sf2_driver_registers.cpp` checks:
- `scaleTuning=0` C2/C3/C4 identical `ipCents` and EMU8000 IP;
- ordinary `scaleTuning=100` retains exact 100 cents per key;
- legacy SF1 `scaleTuning=1` retains its established half-key behaviour;
- all previous P90/P96 Win95 SF2 and DOS regression vectors remain active.

## Hardware A/B proof before promotion

Isolated research code `cd7924036e2173a0040ee456d7436de53e0deaad`, [264-second full reference run #42588019428](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42588019428) SUCCESS with 1/1 targeted `125A_p90_sf2_driver_registers` and P97/P98/P99/P102/P103/P105/P194/P195. The original P193 comparator and real AWE64 Gold analog reference were unchanged. Level-matched spectral comparison:

| Band | Before P196 | After P196 |
|---|---:|---:|
| 50–200 Hz | +2.848 dB | -0.347 dB |
| 200–500 Hz | -1.191 dB | -0.368 dB |
| 500–2000 Hz | +0.157 dB | -0.150 dB |

The 65/131Hz anomalies disappeared in original test times. This is evidence for a targeted actual hardware-reference mismatch, not global physical bit identity.

## Production QA and release boundary

This production commit contains ONLY the two minimal source/test files plus this explanatory documentation. In particular it DOES NOT port research-only P193 legacy wet FX build switches, P194/P195 investigative scripts or temporary public-reference workflows. The current P190/P192 independent full Windows product-suite must run on this exact promoted code: CTests, VST3 module validator, packaged UI/GUI, 125A Plugin Test Lab, PCM/negative oracles and 0%-dry. The previously validated P190/P192 pipeline cannot be retroactively credited to the new P196 code.

- Current source: IMPLEMENTED and **research physical A/B: PASS**.
- Current production Windows complete QA: **NOT RUN until actual push workflow finishes**.
- Physical hardware AWE64 parity over all presets: NOT VERIFIED.
- Real Studio Pro DAW, target-machine ASIO/MMCSS and owner SF2/ROM: NOT RUN.
- FULL independent audit / commercial release: NO-GO.
