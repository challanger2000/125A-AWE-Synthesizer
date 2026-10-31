# P12 — YMF262 hardware rhythm integration

## Hardware sources
Yamaha YMF262 specification:
https://www.bitsavers.org/components/yamaha/YMF262_199411.pdf
Original Nuked OPL3 emulation pinned at:
nukeykt/Nuked-OPL3@765ec962e473aeb767e4cba74ffdc8f588ffbfe8

- Register 0xBD bit5 enables hardware rhythm mode on chip channels 6-8.
- Real five key bits: BD=0x10, SD=0x08, TT=0x04, TC=0x02, HH=0x01.
- BD: channel 6 operators at offsets 0x10,0x13.
  SD: channel 7 operator 0x14.
  TT: channel 8 operator 0x12.
  TC: channel 8 operator 0x15.
  HH: channel 7 operator 0x11.
- B6/B7/B8 melodic key-on must be clear in rhythm mode. Operator values
  come from the corresponding original 16-byte IBK patch.
- Drumming is neither a sampled GM kit nor independent percussion voices.
  5 hardware voices share 3 hardware channel frequency generators.
- Bank index: MIDI note on channel 10. IBK byte 11 selects drum voice:
  6 BD, 7 SD, 8 TT, 9 TC, 10 HH. Other values unmapped. Byte 13 is
  fixed percussion note when nonzero, else MIDI note + signed byte 12.
- Notes are released by the original triggering MIDI key, not transposition.
- One drum per physical drum type, so retrigger replaces former note.
- With active rhythm bank channels 6/7/8 are reserved from melodic
  allocation: 15 available instead of 18. Without bank default unchanged.

## Verification matrix
- Generated 3204-byte IBK with all 5 drum types; exact 0xBD mode/key status.
- Positive real nonzero stereo PCM of separate and overlapping drums.
- Retrigger same drum, NoteOff per type, unmapped notes, CC120 all-sounds-off.
- Fifteen melodic voice allocation boundary in rhythm mode.
- Invalid/missing/non-rhythm bank rejects without destroying valid prior.
- P11 IBK melodic tests and P10 SF2 native tests must remain unchanged.
- V5 serialized state includes drum IBK path and migrates V1/V2/V3/V4.
- Windows VS2022 x64 VST3 + Steinberg 47/47 required on exact commit.
- NOT RUN: original bank fixture, real physical YMF262 PCM traces,
  Studio One project recall and dedicated host MIDI channel 10 playback.
- No copyrighted Creative instrument banks are committed or redistributed.
