# P206 – Actual EMU8000 native register path for original SoundFont Spec Test note59

Research branch only. Original Creative driver trace for note59 remains NOT RUN.

## Why

P200–P205 found a median 81.85-cent EG1 pitch attack mismatch between physical AWE64 Gold CT4390 analog capture and native 125A/86Box. The original P96 Creative-Win95 driver's 64/64 register parity relates to a DIFFERENT private bass SoundFont. It is not proof for public SF2 v3.0 note59.

## Original mapping and important delay

Original public v3.0 note59 is one linked sampleID43 layer with modEnvToPitch=+1200c, delayModEnv=0 timecents, attackModEnv=0 timecents. Note onset 9.5s at 44.1kHz frame 418950.

- Reconstructed original SBAWE.VXD SF2 delay conversion maps timecents zero to ENVVAL 0x7A48: 1464 chip ticks at 725 microseconds, approximately 1.061400 seconds rather than nominal 1.0s.
- Separate original SF2 EG1 attack conversion maps timecents zero to ATKHLD 0x0C. Modeled native full attack phase around 0.989833 seconds.
- Modulation depth PEFE high-byte 0x7F corresponds to +1200 cents.

These predictions do not replace checking the ACTUAL original Creative Win95 register stream for this note. If the original driver writes another ENVVAL, note-on ordering, register clock or voice state, attribution of the pitch mismatch to the chip attack curve is premature.

## Implemented research test

The existing P97 native 86Box renderer now accepts optional --p206-trace and --p206-readbacks flags. Without both flags it has its original behavior. With the flags, it opens the native port-write trace immediately before original note59, checks the selected single voice against its actual ATKHLD/PEFE/ENVVAL registers, and polls the EMULATED chip through ReadDriver every 4410 sample frames over 3 seconds. The I/O trace is closed immediately after the native MIDI NoteOn dispatch and before any deliberate diagnostic readback, so driver-origin I/O reads remain preserved while later probe pointer traffic cannot pollute the note-on stream.

The new P206 analyzer validates native note-on register values and sample timing, and compares readback CPF high-word motion to previously archived P200 native audio pitch bins. All audio, ROM and source bank files remain ephemeral; published evidence contains derived numeric data only. Four negative mutation checks reject incorrect attack, pitch depth, voice and sample timestamp.

Evidence boundary: Native chip register-readback parity is NOT original Creative Win95 driver parity; 86Box readback is NOT physical EMU8000 readback. No production engine or VST3 changes. Independent physical original hardware, full owner ASIO and full audit remain open.

## Next decisive measurement

Run precisely original public SoundFont Spec Test v3.0 program0 MIDI note59 through the previously verified PRIVATE original Win95 Creative guest. Log the genuine SBAWE.VXD port writes, order/timing and register reads, compare against the P206 native note-on trace, and do not use the analog recording as a substitute for actual register evidence.
