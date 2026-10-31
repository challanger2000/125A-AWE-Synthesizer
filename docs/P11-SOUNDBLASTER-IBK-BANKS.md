# P11 Sound Blaster melodic IBK MIDI bank integration

Technical specification: Creative Sound Blaster original .IBK format,
3204 bytes exactly: signature 49 42 4B 1A, 128 x 16-byte timbre structures,
128 x 9-byte NUL-terminated names. Independent parser developed from public
documentation and comparison of the OPL3BankEditor IBK import mapping:
https://github.com/Wohlstand/OPL3BankEditor/blob/master/src/FileFormats/format_sb_ibk.cpp
No GPL bank-editor code copied into the 125A project.

IBK operator values:
  mod 20/40/60/80/E0 from bytes 0/2/4/6/8;
  car 20/40/60/80/E0 from bytes 1/3/5/7/9;
  channel C0 from byte 10 feedback/connection, with OPL3 stereo L+R;
  patch MIDI transpose from signed byte 12; NoteOff uses source MIDI key.
Carrier KSL bits preserved; original carrier TL preserved at full velocity.
MIDI Program selects 0-127 bank index, per channel. For the exposed VST3
Program parameter, all 16 channels use the same program (existing behavior).
The bank is externally supplied, never bundled in public CI or binaries.

Loaded only in Processor::setActive (or state/asset config path resolution).
Never read files or allocate dynamic memory in process, NoteOn or Render.
Audio-thread parameters change which prepared register patch is selected.
Invalid supplied bank file path fails closed (FM muted; EMU8000 unaffected).
Earlier V1, V2, V3 state formats migrate to V4; old bankless projects keep
the single development patch. Restoring or changing an external asset path
while already active still requires reactivation (existing lifecycle rule).

Requirements and evidence for P11:
- Positive: full 128 melodic programs, original-byte preservation and names.
- Negative: malformed signature, truncation, surplus bytes, missing file.
- Failure/rollback: failed bank replacement keeps a prior valid bank.
- Audio: Program 0 and Program 1 render different real FM PCM after selecting
  different synthetic original-register-equivalent patches.
- Pitch: signed transpose +12 causes exact predicted PCM versus same patch
  played an octave higher; NoteOff on source MIDI note releases key.
- Project recall: V4 roundtrip with IBK path, V1-V3 migration, invalid/
  truncated state atomic rejection; actual Studio One save-close-reopen
  remains NOT RUN until owner verifies with original IBK fixture.
- Release: Windows x64 VST3 build and Steinberg 47/47 Validator required.
- Not implemented or claimed: Creative rhythm-mode drums, CQM, 4-op FM
  patch support, Windows driver attenuation model, instrument-bank editor,
  original proprietary bank redistribution, original-hardware audio parity.
