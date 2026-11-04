# P105 – measured filter and envelope release vs physical AWE64 Gold

Real CT4390 analog line output (48 kHz) vs 125A native EMU8000 (44.1 kHz,
resampled only for comparison), original hash-pinned public SoundFont Spec Test
v3.0 MIDI + SF2, *one global level match*. The completed test is
[GitHub Actions #41749832362](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41749832362)
**SUCCESS**, 264 seconds, P97-P105 all passed.

## What was measured

The original test #9 has white noise at progressive SF2 cutoff values.
P105 selects only MIDI notes 39–55 (17 notes) after the spoken announcement,
avoiding its voice overlap. Original test #10 steps resonance; P105 selects
notes 63–71 (9 notes), again after the announcement note has ended.
Measurement windows are 80–320 ms after note-on, before each note-off.

| Item | Result |
|---|---:|
| Filter cutoff: median absolute note-wide level error | 0.161 dB |
| Filter cutoff: signed median level error | -0.066 dB |
| Filter resonance: median absolute note-wide level error | 0.490 dB |
| Filter resonance: signed median level error | +0.490 dB |

These are **level** errors, NOT a guarantee of matching filter resonance
shape, phase or noise spectrum. P105 also reports per-note energy deltas in
80–400 Hz, 400–1500 Hz, 1.5–5 kHz and 5–10 kHz bands. At some low cutoff
settings the broadband deltas are -2.643 dB (MIDI 39), -1.034 dB (MIDI 40),
and +1.343 dB (MIDI 43). A cutoff-band delta as large as +2.219 dB occurs
at note 43 in the 1.5–5 kHz band. The higher cutoff notes 48–55 have note-wide
errors between -0.161 and -0.063 dB.

## Amp and modulation envelope release distinction

P102 checked six-stage note sequences at 1.5–6.5 s (EG2 amp) and
9.5–14.5 s (EG1 envelope modulating pitch). P105 measures the sound's
20 ms RMS fall rates during the 50–400 ms post-note-off window:

| Test sequence | Physical fall | Native fall | Difference |
|---|---:|---:|---:|
| EG2 amp release | -99.616 dB/s | -97.623 dB/s | +1.993 dB/s |
| EG1 mod-to-pitch sequence (output amplitude only) | -98.468 dB/s | -97.584 dB/s | +0.884 dB/s |

**IMPORTANT: The second row measures amplitude, not pitch.** Amp EG2
continues to gate the voice after note-off, and this RMS slope cannot verify
EG1's modulation-to-pitch release. A future EG1 test must measure instantaneous
pitch trajectories using strong single harmonics while the note remains
audible, not just amplitude correlations. P102's 0.9997 is likewise the
**log-RMS correlation of the audio in that EG1 test sequence**, not direct
pitch-envelope identity.

## Decision

The existing 4-point B-spline interpolation and hardware-tuned Chamberlin
filter were already benchmarked against original AWE32 recordings (see
`upstream/AWE32Emu/docs/re-notes/emu8000_tuning.md`). This new independent
CT4390 test corroborates close filter *level* behaviour and close amp release
rate. No DSP change is justified at this stage: a change without additional
evidence risks undoing measured fidelity. Any future targeted low-cutoff fix
must improve the per-note *spectral* residual across cutoffs without regressing
the 157-note AWE32 benchmark, P97-P105, or Windows VST3 tests.

This comparison uses physical analog line out legitimately. Digital
sample-for-sample equality is neither claimed nor required for these
musically relevant conclusions.
