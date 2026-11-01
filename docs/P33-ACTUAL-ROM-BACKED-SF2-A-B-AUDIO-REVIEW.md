# P33 — Actual A/B SF2 merge comparison through identical ROM-backed 86Box EMU8000

Date: 2026-11-01. Research only. **No original Creative Win95 VxD trace for this user bank** and **NO 1:1 hardware claim**.

## Test setup

Original user-provided private `Synth 512 Bank.sf2` (555,754 bytes) and `awe32.raw` (1,048,576 bytes) were used locally, NOT uploaded or committed. Native 125A engine compiled in Ubuntu 24.04 GitHub CI, artifact retrieved and executed **locally** against the two original files, 44,100 Hz / stereo PCM16, note 48, velocity 100, 2 s per program. Both interpretations use identical original ROM and chip/DSP.

Two candidates:
- **P26-additive**: current production default, SF2 specification additions over effective instrument defaults (P21/P26).
- **legacy-fill**: *hypothetical* Creative precedence where preset generators only fill absent instrument generators. Upstream historically verified fill-only behavior with its original Win95 driver on SF1 banks, not necessarily for the user's v2.01 SF2.

### Execution / actual measurements

| Program | Mode | SF2 layers | PCM begins at -40 dBFS | 16-bit peak | Overall RMS |
| --- | --- | ---: | ---: | ---: | ---: |
| 000 Grungy Ramp Bass | **P26 additive** | 2 | **24.58 ms** | **-2.13 dBFS** | -16.08 dBFS |
| 000 Grungy Ramp Bass | legacy fill | 2 | **135.69 ms** | **-9.34 dBFS** | -16.64 dBFS |
| 007 TX81Z Lately Bass | **P26 additive** | 4 | **23.63 ms** | **0.00 dBFS** | -22.13 dBFS |
| 007 TX81Z Lately Bass | legacy fill | 4 | **126.76 ms** | **-6.46 dBFS** | -24.35 dBFS |

The ~100–111 ms onset difference is not due to the core: both modes use the **same actual 86Box chip** and its ~22 ms FIFO. It arises from generator precedence. The P26 version starts after the chip FIFO, while legacy fill adds approximately 100 ms of volume delay.

### Original actual-user P26 continuity

Verified locally that the P33 **P26 additive** WAVs are **sample-for-sample (PCM exact)** with the user's existing P26 WAV recordings (`000_Grungy_Ramp_Bass_EMU8000(1).wav`, `007_TX81Z_Lately_Bass_EMU8000(1).wav`) at the same 44.1 kHz. This proves the test harness did not change the earlier P26 timbre.

The older unsuffixed `000_..._EMU8000.wav` and `007_..._EMU8000.wav` files were from P25, started ~126 ms and are **not** the P26 audio.

### Audible implications

- Program 007 P26: four `W8_1` voices, initial Q generator -10 and fineTune approximately -6/-5; peak hits the 16-bit ceiling briefly (as in P26).
- Program 007 fill: four `W8_1` voices, initial Q generator +100 and fineTune -5/-5; peak 0.4756FS; substantial variation in transient and filtering.
- Program 000 P26: two `Saw_a1` voices detuned +5/-5; fill: both +0. Fill loses detuned beating, changing texture.

All four full-length WAVs and exact measurement data are available in a user-private download `125A_P33_Echter_EMU8000_Klangvergleich.zip`. **Never publish those WAVs**, ROM or bank on GitHub without explicit rights; the repo only carries the source/test infrastructure.

## Code/test boundaries

- Isolated research branch `research/p33-actual-audio-merge-ab`, **not merged**.
- `SoundFont::Bank::diagnosticSf2LegacyFill` defaults to false. True switches only an SF2 bank's preset precedence; SF1 remains unchanged.
- `Synth::SetLastBankSf2LegacyFillForDiagnostics(bool)` must be called offline before playing notes; VST3 does not call it.
- Offline probe option `--sf2-merge additive|legacy-fill` preserves prior default and emits differently named WAVs and voice CSVs.
- Synthetic regression tests verify P26 defaults, legacy precedence, predicted nonzero delay and restoration; same native engine CTests.
- GitHub Actions native Linux builds #41284280819 and #41284418676 passed. No real Win95 driver was run in CI or local.

## Engineering conclusion

**Driver translation matters greatly**, independently of hardware chip DSP. This A/B experiment proves the two plausible software behaviors are audibly different, and that P26's prompt attack is a direct result of its rule.

**It does NOT establish which rule original `SBAWE.VXD` used with a v2.01 SF2.** Blindly changing P26 to legacy would reintroduce the precise delay previously repaired. Retain P26 until an actual 1990s Creative Win95 SF2-driver trace or an independently validated contemporary benchmark resolves this precedence. A Win95 VxD guest image and verified load of this SF2 are not currently available in this research environment.
