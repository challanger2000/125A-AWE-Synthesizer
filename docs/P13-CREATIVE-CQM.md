# P13 — Creative CQM third hardware engine

Source: https://github.com/nukeykt/Nuked-CQM
Pin: 274a4c463ab2f8e193b1c1192f9d4e0d02df521a
Copyright (C) 2026 Nuke.YKT; LGPL-2.1-or-later; CQM 0.9 beta.
Unmodified source files: third_party/Nuked-CQM/cqm.c, cqm.h, LICENSE.
86Box documents Nuked CQM as the Creative clone-FM driver; original
CQM emulation is separate from the established Yamaha YMF262 OPL3 code.

Implementation:
- CQM_Reset native clock 49716 and host output rate, exact upstream
  CQM C implementation. Chip instances are separately allocated before
  audio processing, no audio-thread allocation.
- Shared MIDI note translation, velocity, channel program, IBK bank mapping
  and optional melodic IBK patches target the selected FM core.
  **CQM 0.9 beta drum/rhythm remains disabled** after the generated
  0xBD bassdrum fixture produced no PCM in P13 first test. Yamaha OPL3
  continues to own the validated 0xBD rhythm playback.
- No false equivalence: distinct CQM audio must differ from OPL3 when the
  same register patch is written to each emulator.
- Host native Hardware parameter lists EMU8000 (0), Yamaha OPL3 (1),
  Creative CQM (2). Mode switching releases outgoing FM hardware keys.
- Project state V6 extends the engine enum, preserves all earlier
  asset path records and migration of V1/V2/V3/V4/V5.
- CQM output compensated by same latency the EMU8000 reports to the host.

Gate:
- Native sample-rate, repeatable block-size, note-off, sustain,
  18 voice polyphony, explicit fail-closed CQM drum gating, independent CQM-vs-OPL3 PCM tests.
- Windows x64 VST3 compile, Steinberg validator 47/47 and all CTests.
- Studio One actual CQM playback is NOT RUN until user checks.
- Hardware-measured CQM waveforms, 86Box byte-level CQM parity,
  per-channel MIDI controllers, original Creative ROM/instrument banks
  and new GUI still OPEN.
- CQM is beta, not a proven cycle-exact AWE64 hardware model.
