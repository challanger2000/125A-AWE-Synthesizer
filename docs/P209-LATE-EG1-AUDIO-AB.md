# P209 – Native late-phase EG1 sound proof (RESEARCH ONLY)

P208 tested 2 seconds of original SF2 note59; the physical EG1 delay 1.0614s plus 0x0C attack ~0.99s spans ~2.05s. Therefore bit-exact equality at 2s did not test Hold/Decay at all.

P209 adds an optional native-only --duration-ms (2000..6000), while preserving the P86 default 2000ms. It renders 5.5s of the exact same held original public SoundFont Spec Test note59, velocity100 on 44.1kHz stereo native 86Box EMU8000, baseline versus gated P208 converter candidate.

Test requires equal first 2s PCM, only two changed driver register series ATKHLD/DCYSUS, >1000 genuinely different later stereo frames, and first changed frame between 2.6 and 4.1s, not in attack. Independent negative mutations reject early difference, missing late effect and isolated single-sample change. Only numerical evidence uploaded; raw ROM, SF2, WAV and traces remain ephemeral.

The original Creative driver reference comes from successful P207 original Win95 SBAWE.VXD (virtual AWE64). The actual CT4390 physical AWE64 silicon Hold/Decay behavior and 0x0C attack remain NOT MEASURED by this P209 test. No production DSP change; no release approval.
