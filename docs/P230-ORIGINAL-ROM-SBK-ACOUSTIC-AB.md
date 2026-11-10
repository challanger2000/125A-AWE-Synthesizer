# P230 — Original Wave-ROM + SYNTHGM.SBK: acoustic original-driver A/B

**Status: measurement tools implemented; genuine reference comparison NOT RUN.** No DSP changes; no original Creative or owner media committed. Derived from `fix/creative-volume-sustain-layer-parity` (`2bd6d2d299a53f9af1e741e625d22207e08c8909`). Public GitHub CI can compile these tools and execute synthetic/negative comparison tests, **not** certify original audio fidelity.

## Why this is a stronger independent check

P228's four user-SF2 tests covered 3,082 native renders and found 117 dry PCM rail cases; the engine deliberately did not fall back into GM ROM instruments. P166/P171 established only synthetic ROM/audio behavior, not authentic source timbres. **The genuine 1MiB wave ROM plus `SYNTHGM.SBK` fixes a common original sample corpus and instrument descriptor** for a targeted A/B against the original Creative Win95 `SBAWE.VXD` playback in existing 86Box. This isolates driver register/voice control and chip DSP problems more sharply than mixing unrelated SF2 inputs. Both devices share the emulated 86Box chip model, so even a perfect original-driver/native match does **not** prove physical AWE64 analog or silicon parity.

## Reproducible local native capture

- Build the `awe32_p230_rom_sbk_native` target (`src/engine/CMakeLists.txt`, C++23). CMake uses the same `awe32_chip_safety` production-derived EMU8000 native engine already used by P228.
- Keep genuine `awe32.raw` (exactly 1,048,576 bytes) and **genuine** `SYNTHGM.SBK` (SF1 `1MGM` descriptor, 128 GM plus one GM drum preset) together in a private directory. No file is fetched automatically or copied to the repository. Sample content is read exclusively from original ROM; descriptor supplies GM preset/sample mapping.
- Run `awe32_p230_rom_sbk_native --list` to obtain the exact 397 MIDI tests, or `awe32_p230_rom_sbk_native /private/awe32.raw /private/P230-125A-audio`. The target directory must not already exist. It writes `cases.csv` and 397 separate stereo 44,100 Hz PCM16 WAVs, 2.000 seconds each; NoteOff exactly at 1.000 s, fresh chip per test, no loudness normalization, limiter or gain compensation. It refuses missing/unusable ROM or descriptor and disables fallback to SF2/sine.
- Matrix = GM bank 16383, programs 0..127 at notes 48/60/72 velocity 100, channel 1; plus GM drum bank 16382, program 0 at MIDI notes 35/36/38/42/46/49/51/56/60/64/69/76/81 velocity 100, channel 10. Control baseline: CC7=100, CC11=127, CC10=64, CC91=CC93=0, GUI Reverb/Chorus=0. Each note is rendered through the Win95 driver-family conversion path of our native engine.
- Preserve the private original ROM, SBK, guest image and all created WAVs. Before using reference data, record SHA-256 of ROM and SBK for both runs (they must match), driver binary hash/version, 86Box machine and audio configuration, bank-upload/readback evidence, MIDI-delivery evidence and reference WAV SHA-256 files. Never upload these private artifacts to public Actions.

## Real Creative Win95 reference capture — NOT RUN

Use the **existing** 86Box Windows 95 + authentic Creative `SBAWE.VXD` guest, rather than a new emulator/VM. The ROM must be installed in the emulated card, and `SYNTHGM.SBK` must be loaded/used by the Creative driver, not merely detected by a header/inventory query. Route the identical 397 note/channel/program/CC sequences to the real WinMM original driver. Capture real 44.1 kHz stereo PCM at the same mixer and FX settings without AGC, volume normalization, Windows EQ or limiter. Label every reference WAV using the native `--list` filename; audio provenance must be established separately (a filename is not evidence). Observe and record initial driver-to-chip clock, guest audio capture framing and 86Box mixer gain, and match sample duration/NoteOff before interpreting differences. Do not substitute a generated native waveform for an original driver capture.

Run after the two original sets genuinely exist:

```bash
python tools/p230_rom_sbk_ab.py \
  --reference-dir /private/P230-Win95-Creative-audio \
  --native-dir /private/P230-125A-audio \
  --out /private/P230-ROM-SBK-audio-comparison.json
```

Comparator requires exact one-to-one filenames from `cases.csv`; missing, extra, truncated, silent, mono, wrong-rate and wrong-format inputs are rejected. It computes 10-ms envelope-lag cross correlation (±200 ms), unnormalized RMS/peak offsets, per-channel PCM16 rail counts, and five broad spectral-band energy differences. `NUMERICALLY_CLOSE_NOT_HARDWARE_PROOF` is only a *heuristic*, not a release gate: ±0.5 dB RMS, envelope correlation ≥0.97, all band offsets ≤1 dB, ≤10 rail count difference. Flagged cases must be examined as differences, not automatically corrected with gain hacks or per-preset changes. Comparing waveforms after 10-ms envelope lag alignment is not sample-accurate proof; full sample and register evidence are additional gates.

## Evidence gates and current status

| Requirement | Observable evidence | Current result |
|---|---|---|
| Real ROM + SBK renderer source | Compileable target, strict bank selection, real native PCM writer | SOURCE IMPLEMENTED; CI build pending |
| A/B analyzer quality | Exact-match positive, -6 dB mutant, invalid-format negative control | Local `--self-test` PASS |
| Authentic original assets and preset playback | Original ROM/SBK SHA, Win95 driver sample-bank upload and register readback | NOT RUN in this environment |
| 397 original-driver WAVs | Original WinMM MIDI, actual captured audio, independent provenance | NOT RUN |
| 397 matched A/B comparisons | Native/Original both loaded, valid WAVs, quantitative report | NOT RUN |
| 117 existing SF2 preclip cases | Original Creative SF2 audio comparison with unchanged real SF2 source | NOT RUN; separate P228/P229 gate |
| Physical AWE64 Gold/Studio One validation | Actual hardware capture, exported VST3, target DAW/ASIO | NOT RUN; RELEASE BLOCKED |

This feature produces a **measurement harness**, not a sonic fix. Do not modify the synthesizer's audio, filter, envelopes, FX, output gain, headroom or clipping based on unauthenticated numerical scores. Only a matched true original-driver capture can justify those changes.