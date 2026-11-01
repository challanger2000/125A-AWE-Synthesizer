# P27 — EMU8000 chorus/reverb/pan and output audit (2026-11-01)

Scope: hardware-faithful playback, **not** matching FluidSynth's unrelated effect algorithms. No proprietary ROM, SF2, audio files or samples are committed.

## Audited material

- User's real P26 stereo recordings for `Grungy Ramp Bass` (program 000) and `TX81Z Lately Bass` (program 007), C3/48, velocity 100, 44.1 kHz, WAV16, actual 86Box ROM-backed chip. Audio is available in the private session, not in this repository.
- Real P26 voice CSV shows two 000 voices and four 007 voices.
- `src/engine/Synth.cpp` uses SF2 pan conversion in `SoundFont.cpp`, then maps the sum of patch pan and CC10 into the high PSST byte.
- `src/engine/snd_emu8k.c` routes PSST left and right and processes CSL chorus and PTRX reverb sends; the result is mixed into the PCM bus. The renderer scales by 57737/65536 (-1.1 dB), based on prior physical card measurements.
- Original Creative/E-mu *EMU8000 Programmer's Guide* (pp. 9–10, 21): PSST 0 = extreme right; PSST 0xFF = extreme left; CSL high byte = chorus send; **HWCF4=0** in the official initialization sequence. URL: https://www.dosdays.co.uk/media/creative/emu8kpgm.pdf
- Linux AWE32/EMU8000 driver standard chorus parameters use HWCF4 right-delay value 0 for Chorus 1–4 and Feedback/Flanger, nonzero for Short Delay special modes: https://github.com/torvalds/linux/blob/master/sound/isa/sb/emu8000.c

## Real P26 audio measurements

These values describe the **actual P26 files**, not a claim of bit-exact hardware parity:

| Metric | 000 | 007 |
| --- | ---: | ---: |
| 44.1kHz stereo output duration | 2 sec | 2 sec |
| L/R waveform correlation | ~0.999916 | ~0.999620 |
| Mid/side RMS ratio at 40–250ms | ~0.00270 | ~0.01258 |
| Absolute peak in WAV | ~0.78296 | ~0.99997 |
| Full-scale PCM16 sample count, left | 0 | 15 |
| Transient clipping time span | none | 52.18–52.49 ms |

Program 007's 15-sample clipping burst lasts ~0.34ms (15 samples / 44100 Hz) around the note onset. It does NOT justify an unconditional non-hardware limiter or gain change. Program 007 has two hard-left and two hard-right SF2 preset zones, so the mono-ish sum is compatible with nearly identical left/right sample layers. The reference FluidSynth gain is 0.2 and is not an equal-gain comparison.

In the 86Box chorus model, the stereo tap positions are:
`delay_l = delay_samples_central + triangle_lfo * depth`
`delay_r = delay_l - delay_offset_samples_right`
`delay_offset_samples_right = HWCF4 / 256`.
With correctly initialized HWCF4=0, both chorus return taps coincide: a narrow/mono chorus return is expected from **this model** in its documented standard configuration. This does not establish whether every original hardware/driver effect mode should sound mono, and the full physical-card stereo response remains unverified. Do not change HWCF4 to a made-up value merely to imitate FluidSynth's stereo chorus.

## New isolated synthetic 86Box regression

`tests/sf2_audio_integration.cpp` P27 block renders five independent test notes through the actual 86Box core with a generated zero ROM and a synthetic looping SF2:
1. centre, chorus/reverb send 0;
2. PSST full left;
3. PSST full right;
4. centre with CSL chorus send 255;
5. centre with PTRX reverb send 255.

Assertions: generated PCM audible, both panning extremes route correctly (>=10x channel energy dominance), chorus changes the PCM relative to dry, reverb changes the PCM relative to dry. No copyrighted private assets go into CI. Windows 2022 Engine Safety run #41279159430: **SUCCESS**, 14/14 native CTests. These tests confirm **signal routing and activity**, not hardware audio-sample parity or effect quality.

## Decision / status

- No evidence that the stereo channel wiring is defective.
- No evidence that simple gain reduction or limiting would make it a better hardware emulation.
- The default HWCF4=0 is consistent with the official Creative/E-mu programmer's guide and the standard Linux EMU8000 chorus modes.
- **P26 remains the last verified audible source-bank capture**: the spurious SF2 delay was repaired. P27 adds no timbre-changing patch and requires no new user-side audio test.
- Original-hardware wet-effect parity still requires physical AWE32/AWE64 output measurements or an independently validated golden chip trace. Do not claim final 1:1 accuracy on the basis of FluidSynth.
