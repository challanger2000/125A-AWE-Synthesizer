# P104 – hardware-calibrated SF2 attenuation, CT4390

The original [SoundFont Spec Test v3.0](https://github.com/mrbumpy409/SoundFont-Spec-Test)
describes the AWE32/AWE64 hardware characteristic: an SF2
`initialAttenuation` increment of **5 dB produces about 2 dB** of
actual attenuation at the output. This differs from idealized SF2 rendering.

P103 used five independent unmasked notes (MIDI 65–69, starting at 86.5 s),
the same SF2 file, no per-note gain fitting, and the original AWE64 Gold
CT4390 RCA analog capture. The source-linked test compares the +5 dB
increment in the MIDI test sequence.

| Difference in successive +5-SF2-dB intervals | CT4390 | 125A before P104 |
|---|---:|---:|
| Average slope, MIDI notes 65–69 | +2.258 dB | +4.250 dB |

Evidence: [P103 264s full CT4390 comparison – SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41744716725).

## P104 change

In `SoundFont::MakeVoiceParams`, the Win95 SF2 path now converts SF2
`initialAttenuation` centibels to EMU8000 IFATN register units using the
original AWE's **0.4 output-dB-per-SF2-dB** quirk. This changes
only the SF2 program generator mapping on the Win95 driver variant.
The distinct DOS/SDK SF2 conversion path, SF1 bank conventions,
CC7/CC11/velocity driver curves and underlying 0.375 dB IFATN hardware
step are not changed. P90 synthetic regression vectors cover multiple
attenuations, Win95-versus-DOS differences and all earlier measured drivers.

## Verification and limitations

P103 measures sound levels over the *different* MIDI notes 65–69, which can
contain sample/pitch differences. Its empirical slope is evidence for the
historical 0.4 behavior, not an independent full reverse-engineering of the
SBAWE.VXD SF2 generator branch. Verify that correction reduces P103's
hardware-vs-native relative-slope error without breaking P102 envelopes,
P98 effects, P99 overall fingerprints or Windows x64 VST3/CTest. Do not
misreport PASS as 1:1 acoustic parity; any remaining error should be
analyzed by register-trace or within-note fixture before further tuning.
