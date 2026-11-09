# P199 – AWE64 Gold hardware envelope and sub-50ms timing forensics

**Date:** 2026-11-09. **Question:** Do the original P102/P105 amplitude-envelope and release differences prove a flaw in the current EMU8000 attack/release algorithms, or are they predominantly a test-fixture and capture alignment artifact?

## Evidence and outcome

- **Confirmed original data:** CT4390 AWE64 Gold real analog line-out 48kHz FLAC, same SHA-pinned SoundFont Spec Test v3.0 MIDI (264s) and SF2, native 86Box-derived 44.1kHz synthesis with P193 historically matched FX returns/sends. Reference replay uses the original single global P97 gain. The P193 research-only FX mode is strictly excluded from VST3 binaries.
- **Research code:** `tools/p199_envelope_latency_forensics.py`, latest tested research commit `a88c48d99384e680cc92bfa60a68c879c9ff2bd5`. Full P97/P98/P99/P102/P103/P105/P194/P195/P197/P199 research CI run [#42676193383](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42676193383) **SUCCESS**. JSON evidence: `P199-AWE64-Envelope-Capture-Latency.json`, artifact [#13700971747](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42676193383/artifacts/13700971747).
- **Sonic code:** **unchanged**. This is a measurement correction, not a new release or retuned chip.

### Source-fixture control: not an isolated AMP voice

The original SF2 program 0 note 58 plays two referenced instrument zones: sampleID **43** for the one-second amplitude envelope and sampleID **42** transposed +24 semitones with its own fast-decay envelope. Note 59 plays one referenced instrument zone (sampleID **43**) with an EG1 mod-envelope-to-pitch test. All real preset **instrument links**, instrument zone key ranges and overrides were checked; unreferenced SF2 instrument zones are *not* voices. The first attempt at a new test initially failed because it incorrectly included an orphan instrument zone; test-only fixture selection was corrected and re-run green. Product unchanged.

The original P102 note58 `attack -1.615 dB` and `release +1.55 dB` are **relative output levels of a combined recording**, not direct chip-register or isolated EG2 transfer-curve errors.

### Independent, finer timing diagnostic

P97 coarse whole-recording envelope alignment uses **50ms increments** and found `0ms` at that resolution. Original P102 and P105 contain these independent anchors:

| Metric | EG2 amplitude / note 58 | EG1-to-pitch test / note 59 |
|---|---:|---:|
| P102 native-minus-hardware sustain | -0.897 dB | -0.146 dB |
| P102 native-minus-hardware release | +1.55 dB | +2.285 dB |
| Release minus sustain excess | **+2.442 dB** | **+2.431 dB** |
| Real hardware release slope | -99.616 dB/s | -98.468 dB/s |
| Native release slope | -97.623 dB/s | -97.584 dB/s |
| Apparent lag independently implied by dB/s | **24.51ms** | **24.69ms** |

P199 uses ten-millisecond stereo RMS windows over each NoteOff +55..265ms region. Only for the **numerical comparison**, each curve is scaled by its *own earlier pre-NoteOff plateau*; the actual WAV/FLAC, rendered audio, sample rate, P97 global gain, MIDI/driver and code are unchanged. Searching analysis-only lags from -45..+45ms:

| Original note | Best comparison lag | Median absolute relative release error, 0ms | At best lag |
|---|---:|---:|---:|
| EG2 note 58 | **+22ms** | **2.302 dB** | **0.101 dB** |
| EG1 note 59 | **+24ms** | **2.319 dB** | **0.082 dB** |

The nearly identical independent lags explain the bulk of the misleading phase-level differences in the old 50ms-aligned reports. They do not prove which recording/driver path inserted the lag; do not add a 23ms playback delay to the commercial VST3.

### Hold-out attack validation: no attack-specific fit

Take the **+23ms median lag inferred exclusively from the two release comparisons** and apply it solely to the original test note58's 10ms attack comparison (2.52..3.45s); independently normalize each recording to the hold RMS measured at 3.75..4.15s. No attack-specific shifting or reshaping is fitted.

| AMP attack relative shape | Zero lag | Release-inferred +23ms |
|---|---:|---:|
| Median absolute difference | **0.665 dB** | **0.283 dB** |
| Median signed native-minus-hardware | -0.665 dB | -0.266 dB |

The median absolute shape error drops **~57%** without touching DSP, but **0.283 dB remains**. With two simultaneous sample zones, analog capture characteristics and hardware clock markers absent, it is **not proven** that the remaining difference lies in silicon attack physics rather than voice mixture, filter or capture.

## Engineering decision

1. **Do NOT change** EMU8000 volume attack shape, release rates, stage timing, SF2 attenuation (P198=0.50), pitch, analog EQ, filter or FX based only on P102/P105 pre-alignment figures.
2. P199 establishes high confidence that the dominant old apparent release mismatch is due to the **reference comparison time offset**, rather than a demonstrated 2.4dB gain error. Physical release slope differences of 0.884/1.993 dB/s remain small but not zero.
3. For future sound-fidelity tests, evaluate physical-versus-native envelope phase levels at **sub-50ms timing resolution** and distinguish multi-zone programme outputs from single hardware envelopes. Record the unshifted and aligned metrics, and never apply timing corrections to the commercial PCM without independent hardware evidence.
4. A dedicated single-sample, single-layer, per-register physical hardware capture (ideally controlled digital interface) would be needed to support further exact DSP tuning. It is not currently available in the original reference; do not treat it as a required manual step imposed on the user.
5. P199 is **research validation PASS, DSP change NOT INDICATED**. The last productive code remains P198 `2f986648`, tested SUCCESS [Windows CI #42593301776](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42593301776), 67/67 CTests, 537/537 VST3 validator, 99/99 live GUI interactions, independent Test Lab TECHNICAL_PASS, 0/14,400 lab callback misses. Real target DAW/ASIO and independent FULL AUDIT stay open; **NO RELEASE FREIGABE**.

**Provenance caveat:** Research branch uses P193 native-only historical FX mode, and the P199 envelope test notes do not exercise the separately updated P198 attenuation generator. No production DSP behavior was changed or invalidated by P199. No production VST3 recompile is necessary for this docs-only addition.
