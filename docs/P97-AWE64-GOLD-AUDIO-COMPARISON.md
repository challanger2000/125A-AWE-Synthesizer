# P97 – Genuine Creative AWE64 Gold CT4390 reference

Hardware recording from https://github.com/mrbumpy409/SoundFont-Spec-Test

- Sound Blaster **AWE64 Gold CT4390**, RCA line-out -> RME Babyface Pro FS; playback via Falcosoft SoundFont Midi Player 6.4; AWE Control Panel Hall 1 / Chorus 1, bass and treble at 0 dB
- Audio: 48 kHz stereo, PCM16 FLAC, **264.3634 seconds** (analog capture)
- SoundFont Spec Test **v3.0** historic MIDI/SF2 at Git revision 67c0405ea9: 264 s, **2,200 MIDI channel events**
- Original Git file object SHA-1: MIDI c720631fb2f74f46ce4e2fb0c12be7905353fcfe; SF2 4768c4a0215abf49c7a2bb51ada5ba3494faa1c5; FLAC 9d5fa80197dd6f6170c039cb840e613949546ba9
- Original waveform, SF2 and MIDI are fetched in CI and checked by hash. Do not substitute newer v3.1 files.
- Inventory CI: https://github.com/challanger2000/125A-Engineering/actions/runs/41727051923 — success (8/8)

An offline MIDI-event reader plays the same MIDI on our Win95-profile native 86Box EMU8000 chip with the same SF2 at 44.1 kHz; compare the first 90 seconds to the physical analog recording, resampling ONLY our output to 48 kHz, then computing timing, gain, envelope correlation and band-dependent spectral error.

**Scope is analog hardware characterization, not digital bit-for-bit parity**. Hall1 and Chorus1 and unmeasured input analog components may contribute to differences. Do not adjust the engine to fit analog measurements without investigating independent implementation and driver evidence.

No original Creative ROM, SF2 or FLAC is included in source or uploaded as test artifact. Only numerical report JSON is retained.


## Measured P97 result — 2026-11-03

Verified successful [90-second physical hardware CI run](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41729469575), commit \`7c71229e3d23690af6670cfe8ba3ebe2a1d0779e\`. Metrics downloaded from artifact \`P97-Real-AWE64-Gold-versus-125A-Metrics\`, JSON \`P97-AWE64-Gold-versus-125A-90s.json\`.

- 181 MIDI events in the first 90 seconds; 5,761,504 nonzero stereo PCM samples produced by native 86Box EMU8000.
- 90.0 seconds aligned; reported envelope-based lag 0 ms at **50 ms resolution**, NOT sub-sample synchronization.
- Log-RMS envelope correlation **0.94784** (high similarity in overall envelope shape).
- Mono waveform correlation **-0.02068** (no waveform-level correspondence established).
- Global level alignment **-0.343 dB** for native-to-physical comparison.
- After global level alignment, native-minus-physical integrated spectral energy:
  - 50–200 Hz: **+16.726 dB**
  - 200–500 Hz: **-2.680 dB**
  - 500–2000 Hz: **+0.804 dB**
  - 2000–5000 Hz: **+5.263 dB**
  - 5000–10000 Hz: **+6.255 dB**
  - 10000–20000 Hz: **+7.003 dB**
- In the 64–90 second *filter* section, hardware RMS **0.093618**, native RMS **0.134975**; this signals a specific section to investigate without assigning the cause prematurely.

**Interpretation:** P97 CI SUCCESS demonstrates the reproducible physical-hardware measurement path; it **does not mean the two audio renders match**. Large low-/high-frequency differences remain. High envelope correlation does not resolve the discrepancies. This is a comparison to the 86Box EMU8000 chip model rather than a proven bit-identical physical chip. No production SF2/filter, interpolation, reverb or EQ parameters were changed to fit this analog recording.

**Important limitations before causal conclusions:**

1. CT4390 recording uses analog RCA to a 48 kHz ADC; only the emulated 44.1 kHz output is resampled. Analog transfer response, level processing, and clock differences are uncontrolled.
2. Both reference and native runs are set nominally to Hall 1 / Chorus 1; preset-name agreement does not independently establish the same underlying effects DSP behavior.
3. The spectral measure integrates all active full-second blocks across the first 90 seconds. It is not a per-voice or per-generator filter measurement; the +16.7 dB low-band difference must not be mistaken for a single cutoff parameter error.
4. The comparison excludes the later dedicated SoundFont test sections, so dedicated reverb/chorus 1-to-1 behavior is **not tested** here.
5. S/PDIF capture at native 44.1 kHz and matched dry/wet settings from CT4390 would help separate synthesizer discrepancies from the analog recording chain. The public test result is not a substitute for that hardware capture.

**Next evidence-driven work:** measure spectra and stereo behavior by individual test segment; verify CC/NRPN MIDI-event handling and effect-state setup; request the digital S/PDIF reference; compare dry single-note sample/filter/loop curves separately before changing the audio engine.


## Full 264-second hardware comparison — verified SUCCESS

Full test [Actions #41730602579](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41730602579), commit \`b8ccbf79938543a1cf77dddb1b968b694d284d48\`, succeeded after fixing the 264s WAV filename in the workflow. It rendered 264s, dispatched 2,199 MIDI events within that finite time window and uploaded the original numerical report with a per-section breakdown. The predecessor [#41729977888](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41729977888) failed only because it attempted to open \`native-90s.wav\` after rendering \`native-264s.wav\`.

### Global metrics (hardware CT4390 analog vs native 86Box EMU8000)

| Measurement | Full 264s |
| --- | ---: |
| Log-RMS envelope correlation | 0.95155 |
| Mono waveform correlation | 0.01049 |
| Coarse envelope-alignment offset | 0 ms (50 ms bins; not phase alignment) |
| Global native gain adjustment | -0.179 dB |

Frequency band difference (native minus analog reference; after global gain match):

| Hz | dB |
| --- | ---: |
| 50–200 | +2.456 |
| 200–500 | -1.483 |
| 500–2000 | +0.280 |
| 2000–5000 | +4.872 |
| 5000–10000 | +5.924 |
| 10000–20000 | +7.140 |

The earlier **+16.726 dB at 50–200 Hz is first-90s-only**, not a whole-recording discrepancy. The spectral tilt above 2 kHz is widespread and is not confined to the SoundFont low-pass filter test.

### Critical segment results

| Original test section | CT4390 RMS | 86Box native RMS | Envelope correlation |
| --- | ---: | ---: | ---: |
| 09 Filter cutoff (64.5–76.5s) | 0.079871 | 0.150714 | 0.93177 |
| 10 Filter resonance (76.5–84.5s) | 0.064179 | 0.123641 | 0.93762 |
| 14 Velocity to filter (126.5–157.5s) | 0.037317 | 0.058928 | 0.93430 |
| 17 Reverb (169–198.5s) | 0.052302 | 0.046041 | 0.95388 |
| 18 Chorus (198.5–228.5s) | 0.046945 | 0.054561 | 0.95631 |
| 20 Pitch bend (237.5–260.5s) | 0.262520 | 0.263973 | 0.96345 |

The filter sections show larger native RMS than real hardware, and the high-frequency excess appears in many other sections, too. Test 03/04 low-band spectral ratios exceed +20/+30 dB, but very small reference band energy can inflate log ratios; do not treat these as gain controls or fix targets without inspecting absolute powers.

### Status and boundaries

- **COMPLETE:** full 264s original hardware comparison pipeline, deterministic original v3.0 MIDI/SF2, per-section numerical metrics, successful CI.
- **NOT PROVEN:** 1:1 digital/audio accuracy, individual reverb/chorus DSP parity, physical sound-card filter shape, or waveform phase correspondence.
- The 86Box output and a real CT4390 may differ at the actual audio-rendering layer even when the original Win95 driver register series match.
- Additional EQ ambiguity: the 125A core defines measured EQ shelves, but its 86Box render path takes the 86Box chip PCM output rather than the core's auxiliary floating-point FX/EQ render. Therefore one must verify what EQ behavior is actually implemented in the 86Box chip path and what settings the CT4390 reference used; do not simply add compensating EQ to conceal a source mismatch.
- **Next priority:** controlled 44.1 kHz S/PDIF capture from physical CT4390 with matched v3.0 SF2/MIDI and FX settings, ideally plus a dry run. Until then, preserve the production audio engine unchanged and investigate mismatch by individual test segments and original chip behavior.


## P97: Complete real AWE64 Gold CT4390 acoustic comparison (verified 2026-11-03)

- [Full 264-second P97 CI #41730602579](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41730602579): **SUCCESS, 12/12 steps**; 21 historical SF2 test sections, 2,199 MIDI messages.
- **CT4390 analog RCA recording**: 48kHz stereo PCM16 FLAC, Hall 1 / Chorus 1; 125A genuine 86Box EMU8000 chip rendered original v3.0 SF2 and MIDI at 44.1 kHz, then resampled to 48 kHz for numeric comparison only. The reference has an unknown analog output / ADC transfer function.
- **Log-RMS envelope correlation = 0.95155** (264s, 50ms bins); waveform correlation = 0.01049, so NOT a sample-exact digital match. Gain matching −0.179 dB. Coarse timing offset 0 ms with 50 ms resolution; not a sample-accurate latency measurement.
- Relative native versus physical after global gain match: 50–200 Hz +2.46 dB; 200–500 Hz −1.48 dB; 500–2000 Hz +0.28 dB; 2000–5000 Hz +4.87 dB; 5000–10000 Hz +5.92 dB; 10000–20000 Hz +7.14 dB.
- In the native P97 render Hall 1 / Chorus 1 were programmed via EMU8000 INIT/HWCF5 registers for this test. Original production sound engine remains unchanged.
- Numerical JSON artifact is under the full P97 CI run; neither original FLAC nor ROM nor test SF2 is redistributed in source or CI artifacts.

### Focus areas from section-by-section results

| SoundFont test | CT4390 analog RMS | 125A RMS | envelope correlation | Priority |
|---|---:|---:|---:|---|
| Volume envelope | 0.153282 | 0.136022 | 0.97066 | Compare envelope shape after per-note gain alignment |
| Initial filter cutoff | 0.079871 | 0.150714 | 0.93177 | Native +5.52 dB RMS; verify filter, gain and old AWE filter shape |
| Filter resonance | 0.064179 | 0.123641 | 0.93762 | Native +5.70 dB RMS; verify hardware Q limiting |
| Velocity-to-filter | 0.037317 | 0.058928 | 0.93430 | Native +3.97 dB RMS; check AWE-era velocity semantics |
| Reverb | 0.052302 | 0.046041 | 0.95388 | Native −1.11 dB RMS; isolate wet/dry |
| Chorus | 0.046945 | 0.054561 | 0.95631 | Native +1.31 dB RMS; isolate wet/dry |
| Interpolation | 0.121614 | 0.117680 | 0.96228 | Within 0.29 dB RMS; inspect per-note spectral slope |
| Pitchbend | 0.262520 | 0.263973 | 0.96345 | Within 0.05 dB RMS; requires pitch tracking |
| Exclusive class | 0.041540 | 0.066821 | 0.92197 | Native +4.13 dB RMS; investigate cut-off/release |

Overall high-frequency differences occur even outside the dedicated filter tests; they cannot all be assigned to the EMU8000 filter. The output reports a maximum magnitude of 32768 on PCM16: quantify clipping prevalence separately.

### Next proof gates

1. Isolate dry constant-note and white-noise test windows and measure actual per-note spectrum and envelopes rather than whole-section mixed power.
2. Ask the original CT4390 recording contributor for **44.1 kHz lossless S/PDIF** of the same historic v3.0 test, both effects on and off, if possible. Current contributor issue: https://github.com/mrbumpy409/SoundFont-Spec-Test/issues/2.
3. Separate effects and analog signal-chain contributions; characterize timing drift, hardware frequency response and sample-rate conversion.
4. Do not alter production DSP based on generic global EQ or claim physical 1:1 accuracy. P96 64/64 original Win95 note register history remains the gate for any justified change.

**P97 measures real analog hardware similarity; it does not establish bit-accurate physical hardware parity.**


## P97 flat-EQ correction verified — 2026-11-03

The published physical CT4390 recording has bass and treble **0 dB**, but the native Win95 EMU8000 initial register array previously left the emulated treble shelf at **index 9 (+7.9 dB)**. P97's renderer now writes only the original Creative INIT3/INIT4 register words for **bass index 5 / treble index 5 (0 dB / 0 dB)** and reads the registers back, failing on an incorrect decode. This is an acquisition-condition correction in P97, **not** a fitted spectral equalizer or a modification of the VST3 production engine. The original 264-second MIDI, FLAC and SF2 hashes are unchanged.

- Fix: [commit 8fa0b77](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/8fa0b77196ca8bc526000ea99754d112bcbc40d0).
- Original 264-second comparison (unmatched EQ): [run #41730602579](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41730602579), SUCCESS.
- Retest with matching real-hardware 0 dB EQ: [run #41731911493](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41731911493), SUCCESS. Run log: \`P97 CT4390 matched 0 dB equalizer: bass 5/5, treble 5/5; Creative INIT3/INIT4 registers verified\`.

### Global spectrum: native minus physical, equal-level matched

| Band (Hz) | Original incorrect test | Matched-EQ retest |
|---|---:|---:|
| 50–200 | +2.456 dB | +2.943 dB |
| 200–500 | −1.483 dB | −1.180 dB |
| 500–2000 | +0.280 dB | +0.263 dB |
| 2000–5000 | +4.872 dB | **+0.164 dB** |
| 5000–10000 | +5.924 dB | **−0.525 dB** |
| 10000–20000 | +7.140 dB | **−0.085 dB** |

Global envelope correlation increased from 0.95155 to **0.95402**; waveform correlation remains poor (**0.01349**, from 0.01049), so bit-level or phase matching is NOT established.

### Previous "1.9x filter RMS" discrepancy was primarily a test-configuration artifact

| Test section | Native / hardware RMS, unmatched | Native / hardware RMS, matched EQ |
|---|---:|---:|
| Filter cutoff (64.5–76.5s) | 1.887× | **0.974×** |
| Filter resonance (76.5–84.5s) | 1.927× | **1.047×** |
| Velocity to filter (126.5–157.5s) | 1.579× | **1.035×** |
| Exclusive class (260.5–264s) | 1.609× | **0.983×** |

These section RMS comparisons do **not** demonstrate exact cutoff curves, resonance/Q or envelope timings. They only invalidate the earlier inference that the 1.9x ratio by itself proves a faulty filter.

### Remaining acoustic discrepancies — P97 is OPEN

- **Reverb section 169–198.5s:** native/hardware RMS **0.749×**, high band 10–20 kHz **−5.754 dB**. It requires a dedicated return/tail and timing investigation, plus recording-condition verification. Do not raise reverb gain on speculation.
- **Attenuation section 84.5–90s:** native/hardware RMS **0.795×**.
- **Volume envelope 0–8s:** 0.866×; mod LFO 40–50s: 0.867×.
- **Keynum-to-decay/hold:** some narrow spectral ratios remain anomalously high in bands with low reference energy. Need absolute power, time alignment and distinct test-note segmentation before attributing to chip/filter.
- **Digital S/PDIF reference** at 44.1 kHz with exact MIDI/SF2/effects settings is still not available. Analog RCA at 48 kHz cannot establish sample-level hardware parity.
- Hardware EQ is now matched for this experiment; that does **not** imply that the emulation's power-on defaults should universally change, because original DOS/Win95 Creative configuration may intentionally vary.

**Acceptance remains unmet:** matching RMS and broad-band spectra is necessary but not sufficient for the 1:1 hardware goal. Leave P97 open; retain original measurements as a documented invalid-control condition, not as evidence of a 7 dB chip error.
