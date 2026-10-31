# 125A AWE Synthesizer P10 — YMF262 OPL3 MIDI integration

## Scope

- Self-contained Opl3Midi audio/MIDI adapter links to pinned Nuked OPL3 core.
- 18 channels in 2-operator, non-rhythm mode. Key-on, key-off, velocity-to-TL,
  bounded oldest-released/oldest-active voice stealing. Native tests cover
  duplicated notes, sustain and all-notes-off.
- Existing VST3 sample-offset event loop now dispatches NoteOn/NoteOff
  to selected hardware; Hardware parameter is a StringListParameter with
  AWE32/64 EMU8000 as backwards-compatible default. No bespoke GUI yet.
- FM output is delayed by existing EMU8000 reported FIFO latency whenever
  active so host PDC remains stable during a live mode change.
- Serialized state V3 adds a hardware-engine word. V1/V2 parse and migrate
  to EMU8000. Invalid/truncated state must not mutate prior state.
- No large allocations, mutexes, filesystem, or blocking work in audio
  callback. Both engines are allocated on activation.

## Evidence requirements

1. Native 125A_opl3_midi_audio: real audible PCM, exact block partition
   equality, 18-channel allocation, 19th-note stealing, note-off/repeated
   notes, sustain and 128-frame latency alignment.
2. Native 125A_asset_state: V1/V2 compatibility and V3 hardware recall,
   invalid engine and truncation rejection.
3. Full Windows x64 VST3 build and Steinberg 47/47 Validator, all native CTests.
4. Studio One: note on/off, live switching, save-close-reopen OPL3 project,
   rapid retrigger, offline render, editor lifecycle, latency behavior.
5. Original Yamaha/Creative FM bank mapping is NOT IMPLEMENTED. Temporary
   test patch verifies event path, not original 128-preset GM assignment.
6. Creative CQM is different from Yamaha YMF262. CQM and Live!/EMU10K1 modes
   have NOT been implemented.

## Licenses and assets

Nuked OPL3 LGPL-2.1-or-later, original attribution/license included.
86Box GPL-2.0-or-later obligations remain relevant to release.
Never commit Creative ROMs, commercial FM banks or third-party drivers.
