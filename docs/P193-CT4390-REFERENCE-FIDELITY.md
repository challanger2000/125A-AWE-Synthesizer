# P193 – Physical CT4390 AWE64 Gold comparison on P190/P192

Status: test-only research branch, no production build / release approval.

## Proven comparison-contract regression

The original P97 reference tool programs the CT4390 "Hall 1" and "Chorus 1"
effect types through the authentic INIT/HWCF registers, and matches the
hardware control panel's 0 dB bass/treble. However, starting with P190,
a newly constructed 125A `Synth` intentionally starts both GUI FX controls
at **0% = OFF**, `MuteEffectReturns(true,true)`, and all SF2/CC-derived
`PTRX[15:8]` and `CSL[31:24]` voice sends are forced to zero.

Thus building P97 unchanged from current P190 code would compare a DRY plugin
against a reference CT4390 capture with effects enabled, producing **invalid
FX-fidelity evidence**. This is a bug in the historical test setup, NOT an
identified defect in the shipped P190 dry-at-zero behaviour.

Turning both 125A GUI controls to 100% is NOT an acceptable solution:
`FxSendLevel::Apply` at 100% maps every send to 255, whereas the original
Creative Win95 driver computes `clip(patch_send + floor(CC*90/100), 0,255)`
separately for every voice. It would produce a different reference experiment.

## Isolated solution

The opt-in CMake option `AWE125_P193_CT4390_REFERENCE_FX=ON` modifies ONLY
the specifically compiled standalone native chip probe:
- The FX return mask starts unmuted.
- Per-note FX send registers are assigned their **original** Win95/SF2/CC
  levels, retaining all original Creative preset and register calculations.
- The real 86Box filter/chorus/reverb/synthesis algorithms, EQ tables,
  resampling and recording analysis are completely unchanged.
- Building this option with `125A_BUILD_VST3=ON` fails at CMake time. The
  default is OFF and production VST3 keeps P190's absolute dry contract.
- The P97 renderer fails closed if built without this test-only option.
- The reference renderer checks both Hall and Chorus registers actually
  exhibit nonzero intermediate send levels (1..254), so even a superficially
  green all-dry or all-255 render cannot count as evidence.

The separate P193 CI job pins the existing P97 original MIDI/SF2/CT4390 FLAC
hashes and uses an ephemeral ROM, without uploading any ROM/audio fixture.
It runs the original complete 264 s MIDI timeline and P97/P98/P99/P102/
P103/P105 objective analyses on the **current product source base**.
The previous P97–P105 numerical results remain valid *only for their recorded
historical source versions and capture conditions*, not automatically for P190.

## Required evidence / decision gates

| Requirement | Gate |
|---|---|
| Default production dry behaviour | Existing P190 CTests/VST3 regression, unchanged |
| Test-only build cannot affect VST3 | CMake configure must reject simultaneous reference+VST3 flags |
| Historical FX sends preserved | Actual PTRX/CSL intermediate register observations |
| Non-silent reference render | Full 264-second genuine 86Box PCM generation |
| AWE64 matched settings | CT4390 FLAC + pinned MIDI/SF2 + Hall1/Chorus1 + flat EQ |
| Spectrum, envelopes, release, effects | P97/P98/P99/P102/P103/P105 actual JSON reports |
| AWE64 waveform identity | NOT CLAIMED: analog RCA/ADC path and independent clocks |
| Hardware-real-time/ASIO | NOT RUN in this benchmark |
| Commercial release | NO-GO |

No global gain compensation, reverb gain boost, envelope retuning, chorus
rounding or filter rewrite may be inferred from this contract repair.
A specific measured residual must first survive the matched settings and an
independent negative/falsification control. Old branch/source results and
new branch/source results must not be silently combined.
