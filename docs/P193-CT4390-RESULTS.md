# P193 – completed current-source AWE64 Gold CT4390 fidelity measurements

Date: 2026-11-09. **Windows product code / P190 commercial 0%-dry behaviour unchanged.**
Research branch: `research/p193-ct4390-fidelity`.
Exact workflow source SHA: `8472731a5883b7c09893c574ccc944608e47bb58`.
[Completed CI run #42584492536](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42584492536): SUCCESS.
[Unmodified numerical reports (artifact 13657779317)](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42584492536/artifacts/13657779317).

## Experimental controls actually verified

- Source, original 264-second MIDI/SF2, CT4390 analog FLAC pinned by Git object hashes.
- Full 264 s rendered through actual 86Box EMU8000 backend: 2,199 MIDI events, 15,567,210 nonzero PCM channel samples.
- Original CT4390 Hall1/Chorus1 effect programs and Creative 0-dB/0-dB INIT EQ independently read back.
- Test-only 125A reference engine uses **original per-voice patch + CC91/93 historical FX sends** and unmutes both FX returns.
- Probe observed seven intermediate Hall and seven intermediate Chorus register values (nonzero, below 255). This falsifies both an all-dry test and blindly setting 125A FX to 100%, which would force 255.
- CMake negative control verified the physical reference option **cannot** be combined with VST3 build.
- P97, P98, P99, P102, P103, P105 completed and wrote numerical artifacts. No hardware-real-time, genuine user-SF2 or release audit is claimed.

## Actual latest measurements

The analysis applies one hardware/native gain match (+0.225 dB applied to native for P97 comparison); it does NOT independently normalise each section or post-EQ the waveform. Analog hardware output was digitized at 48 kHz, the 86Box chip rendered 44.1 kHz and was resampled for analysis.

| Diagnostic | Latest current-source result | Interpretation |
|---|---:|---|
| 50–200 Hz, native minus hardware, globally level matched | **+2.848 dB** | Material low-bass imbalance; investigate spectrum/sample and analog transfer before EQ changes |
| 200–500 Hz | −1.191 dB | Low-mid imbalance remains |
| 500–2,000 Hz | +0.157 dB | Small aggregate difference |
| 2,000–5,000 Hz | +0.016 dB | Nearly matched in this aggregate |
| 5,000–10,000 Hz | −0.672 dB | Residual upper-mid difference |
| 10,000–20,000 Hz | −0.191 dB | Small aggregate high-band difference |
| 50ms log-RMS envelope correlation, 264s | 0.95281 | Strong broad envelope correlation, not waveform identity |
| Raw waveform correlation | 0.01151 | NOT a valid phase-parity gate: clocks, analog ADC and sub-sample drift uncontrolled |
| Filter-cutoff median absolute note level error | 0.161 dB | Near in level, not guaranteed cutoff curve fidelity |
| Filter-resonance median absolute note level error | 0.490 dB | Near in level, not guaranteed Q/shape fidelity |
| EG2 amp envelope: coarse log-envelope correlation | 0.9735 | Attack and release phase details still differ |
| EG2 amplitude attack, globally matched | −1.614 dB | Phase-level residual |
| EG2 amplitude release, globally matched | +1.546 dB | Phase-level residual |
| EG2 post-note release slope | HW −99.616 / native −97.623 dB/s | Native falls 1.993 dB/s more slowly in this window |
| P103 effective attenuation per +5 SF2 dB | HW 2.258 / native 1.700 dB | **−0.558 dB** relative slope; source test changes MIDI note pitches |
| P99 Hall1 max-send A/B/C body level errors | −0.513 / −0.465 / −0.484 dB | Correction P101 remains reasonably close for this specific fixture |
| P99 Chorus1 max-send A/B/C body level errors | +0.265 / +0.589 / +0.041 dB | Correction P100 remains reasonably close for this specific fixture |

The 0%-send note in each FX group is approximately +1.3 to +1.4 dB on the native side after a single global level match; this is a separate **dry-source** residual, not evidence to boost or cut only the effects.

## Next justified fidelity priority

**First:** Identify why the dry low-bass energy differs by ~2.85 dB in the global 50–200 Hz band without changing filter or master gain on speculation. Inspect per-note absolute power and the original analog chain's low-band transfer. A whole-song spectral difference mixes pitch, instrument, reference ADC and FX sections; it is insufficient to propose a corrective EQ.

**Second:** Quantify EG2 onset and tail shape in aligned single-note windows, especially the measured −1.61 dB attack and +1.55 dB release residual. The AWE64 recording's time/clock uncertainty precludes sample-precise decay claims.

**Third:** Resolve the +5dB-SF2 attenuation step slope difference with an independent same-pitch/same-sample hardware measurement or validated original Creative-register trace. The existing P103 source sequence uses MIDI notes 65–69; frequency/pitch/sample differences can confound per-note loudness. Do **not** retune P104's existing calibrated 0.4 mapping solely to force this number.

**Lower priority:** The P100 Chorus1 and P101 Hall1 level corrections, already within roughly ±0.6 dB for three max-send fixtures; no demonstrated benefit to further arbitrary effect gains. A matched 44.1kHz digital S/PDIF capture with documented dry/wet states and start/end synchronization would separate hardware DSP fidelity from analog ADC/source effects.

## Decision

- **P193 matched comparison chain: PASS** (native-only research).
- **Physical EMU8000 exact silicon/audio parity: NOT VERIFIED**.
- **Normal Windows VST3 / DAW / ASIO on current research branch: NOT RUN**; the proven P190/P192 production CI result remains the earlier, untouched source.
- **FULL AUDIT / commercial release: NO-GO**.

No product DSP change is justified solely by aggregate hardware mismatch, even with a successful comparison run.
