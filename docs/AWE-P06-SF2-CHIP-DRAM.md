# AWE-P06 — SF2 -> native/86Box DRAM end-to-end

Status: **candidate**. CI evidence is required before PASS.

## Root cause
`Synth::LoadBank` uploaded SoundFont sample words solely to the C++ model DRAM
and never propagated newly loaded audio to the active 86Box EMU8000 DRAM.
The result was successful bank parsing/preset selection yet missing sample
material on the actual chip path. Switching to 86Box *after* loading a bank
also failed to copy the already-populated model DRAM. A 512KB chip could
accept an oversized SF2 without a capacity error.

## Correction
- Check physical 24-bit address bounds and active chip DRAM capacity before
  any sample memory or bank-list mutation. This is a transactional failure.
- On success, copy **postprocessed** (including SF1 filter) sample words into
  the active 86Box chip DRAM, including the zeroed reserve on first bank load.
- On chip activation after banks have loaded, migrate existing DRAM if it fits,
  otherwise reject activation before mutating the current chip mode.
- Maintain the existing 16-word Win95 / 50-word DOS sample start reserve.

## Test coverage
`125A_sf2_audio_integration` creates a copyright-free SF2 RIFF bank with
actual embedded sine PCM, instrument zone, preset and sample headers. It
checks native NoteOn -> audible PCM; active 86Box chip memory receives the
same sample words; oversized 512KB chip upload rejection leaves the first
bank unchanged; chip switch after earlier SF2 loading carries the data.
These assertions must fail if the SF2 voice route or chip RAM transfer is
broken. All assets are synthesized temporarily in the test; none are
committed or exported.

## Explicitly NOT RUN
- Actual private FM Dreams / Synth 512 Bank / Callanish timbral playback.
- Original `awe32.raw` vs real hardware sample-by-sample parity.
- Windows VST3 factory/processor/controller, Steinberg validator and DAW.
