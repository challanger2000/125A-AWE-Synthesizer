# P98 — external EMU8000 primary evidence and next hardware experiment

Status: **research complete / acoustic parity OPEN**, 2026-11-03.
P97 flat-EQ retest is successful, but sound-chip and physical-effects parity are not proved.

## New independently sourced evidence

1. **Original chip designer Dave Rossum** says EMU8000 used a custom **24-bit effects engine** and a cost-reduced G-chip pitch-shifting algorithm, internally nicknamed G0.5. The proprietary effects DSP should not be conflated with the 16-bit sample format. [Rossum interview](https://www.amazona.de/interview-dave-rossum-e-mu-english-version-part-four/).
2. **Creative's contemporary AWE32 FAQ**, archived from Creative BBS, says the effect engine is a dedicated reverb/chorus/QSound design *not intended to be user-programmable*. The Windows driver can select effect variants by SysEx; this does not expose the underlying internal DSP network or provide a bit-accurate algorithm. [Creative FAQ](https://groups.google.com/g/comp.sys.ibm.pc.soundcard.tech/c/HlU80VrCVGI).
3. **Creative AWE32 Developer's Information Pack v3.00, page 92** documents a **16-entry resonance coefficient table**; cutoff, resonance and DC attenuation depend on coefficient selection. This is an independent characterization target for the filter, not license to patch the current response without matching stimulus/settings. [HTML transcription of original manual](https://www.manualslib.com/manual/2031598/Creative-Awe32.html?page=93).
4. The **original Linux EMU8000 driver** contains the genuine **28-word hall preset register arrays** and **five chorus parameter groups**; its write APIs prove *control register inputs*, not the internal effects DSP topology. [Linux original-driver source](https://github.com/torvalds/linux/blob/master/sound/isa/sb/emu8000.c).
5. **Creative's AWE64 manual** documents EMU8000 audio on the digital **S/PDIF output**, nominally at 44.1 kHz. The CT4390 has a compatible external connector, making a direct-digital reference a realistic request. [AWE64 original manual transcription](https://manualzz.com/doc/823248/creative-awe64---value-sound-card-specifications), [CT4390 hardware survey](https://dosdays.co.uk/topics/Manufacturers/sb_awe32_64.php).
6. [Original SoundFont Spec Test v3.0 README at the **exact** test revision](https://github.com/mrbumpy409/SoundFont-Spec-Test/blob/67c0405ea9/README.md) describes:
   - Test 17 reverb A: instrument send only; B: CC91 only; C: both, each at 0 / 33 / 67 / 100%.
   - Test 18 chorus A: instrument send only; B: CC93 only; C: both, each at 0 / 33 / 67 / 100%.
   This is crucial: a single overall 29.5-second RMS ratio obscures whether the send mixer, effects return, or both differ. Compare the subtests independently.

## Methodological correction required in P97

The existing P97 \`mono_audio_correlation\` (~0.01349) is **not a valid waveform-parity failure criterion**. \`tools/p97_compare_hardware_audio.py\` aligns 50-ms *RMS envelope bins*, then compares waveforms decimated by picking every 48th 48-kHz frame (without sample-level alignment or anti-alias filtering). Analog ADC sample-clock drift, channel delays, effects phases, and sub-millisecond offset can force Pearson correlation near zero **even for otherwise similar periodic waves**. Example: a 1-kHz sinusoid shifted by 12 samples at 48 kHz has cosine correlation near zero (quarter-cycle shift). Do not interpret the raw zero as evidence of incorrect chip output.

Before a waveform-level or 1:1 claim:
- Use sample-level cross-correlation on short isolated dry note segments *with anti-alias-safe handling*.
- Estimate clock drift and channel-specific alignment independently, and separate wet from dry before phase tests.
- Compare dynamic per-note amplitude, individual frequency-response/resonance curves, and reverb impulse/tail envelopes, not only aggregate section RMS.

## Verified local facts

- P97 original 264s unmatched-EQ result +7.14 dB at 10–20 kHz was **confounded by native default treble index 9 (+7.9 dB)**.
- P97 flat-EQ CT4390-matched run [#41731911493](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41731911493) achieved -0.085 dB at 10–20 kHz and 0.164 dB at 2–5 kHz after global gain matching; filter section RMS is close. This proves the test setup previously caused a major false positive, not full chip parity.
- P97 Hall1 aggregate instrument/CC91 test still differs (native/hardware RMS ~0.749) with upper-band deficits; the current 86Box-derived \`src/engine/snd_emu8k.c\` explicitly uses the **fitted** \`REVERB_FITTED\` comb/allpass algorithm, not a proven silicon implementation.

## Actionable experimental protocol (NO speculative DSP tuning)

1. Parse original v3.0 MIDI note, program, channel and CC91/93 events; identify exact start/end of every A/B/C variation rather than equal-duration guesses.
2. On the existing CT4390 analog FLAC and native P97 render, measure each A/B/C event with (a) first 100–200ms onset, (b) 200–1000ms sustain, (c) post-release tail at 100ms increments. Normalize once on matched dry-signal anchor notes, not separately for each wet event.
3. If A is accurate but B is not, investigate MIDI CC91 conversion / channel send; if A and B both differ with similar tail shape, inspect reverb return/DSP; if tail decay slopes differ, model structure or feedback differs. Make no gain fix until these are separated.
4. Request **CT4390 44.1-kHz lossless stereo S/PDIF** with original v3.0 SF2/MIDI, same Hall1/Chorus1 and 0dB tone settings; a second dry run with reverb and chorus send disabled will provide an oscillator/filter control. Do not normalize/EQ/limit either capture.
5. Independently benchmark the original Creative resonance coefficient table against actual low/high cutoff behavior, under fixed noise and matched EQ, not using whole-section RMS.
6. Retain P97 **OPEN** until credible silicon-level or independently controlled digital-hardware evidence supports the fidelity claims.

No physical S/PDIF recording or independently verified internal EMU8000 effects algorithm was found in this research pass. The Creative reference materials and user-supplied SF2 data should not be redistributed.
