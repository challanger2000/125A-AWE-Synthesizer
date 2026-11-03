# P97 – Genuine Creative AWE64 Gold CT4390 reference

Hardware recording from https://github.com/mrbumpy409/SoundFont-Spec-Test

- Sound Blaster **AWE64 Gold CT4390**, RCA line-out -> RME Babyface Pro FS; playback via Falcosoft SoundFont Midi Player 6.4; AWE Control Panel Hall 1 / Chorus 1, bass and treble at 0 dB
- Audio: 48 kHz stereo, PCM16 FLAC, **264.3634 seconds** (analog capture)
- SoundFont Spec Test **v3.0** historic MIDI/SF2 at Git revision 67c0405ea9: 264 s, **2,200 MIDI channel events**
- Original Git file object SHA-1: MIDI c720631fb2f74f46ce4e2fb0c12be7905353fcfe; SF2 4768c4a0215abf49c7a2bb51ada5ba3494faa1c5; FLAC 9d5fa80197dd6f6170c039cb840e613949546ba9
- Original waveform, SF2 and MIDI are fetched in CI and checked by hash. Do not substitute newer v3.1 files.
- Inventory CI: https://github.com/challanger2000/125A-Engineering/actions/runs/41727051923 — success (8/8)

An offline MIDI-event reader plays the same MIDI on our Win95-profile native 86Box EMU8000 chip with the same SF2 at 44.1 kHz; compare the first 90 seconds to the physical analog recording, resampling ONLY our output to 48 kHz, then computing timing, gain, envelope correlation and band-dependent spectral error.

**Scope is analog hardware characterization, not digital bit-for-bit parity**. Hall1 and Chorus1 and unmeasured input analog components may contribute to differences. Do not adjust the engine to fit analog measurements without investigating independent implementation and driver evidence.

No original Creative ROM, SF2 or FLAC is included in source or uploaded as test artifact. Only numerical report JSON is retained.
