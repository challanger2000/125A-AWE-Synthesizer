# P209 – Native late-phase EG1 sound proof (RESEARCH ONLY)

P208 tested 2 seconds of original SF2 note59; the physical EG1 delay 1.0614s plus 0x0C attack ~0.99s spans ~2.05s. Therefore bit-exact equality at 2s did not test Hold/Decay at all.

P209 adds an optional native-only --duration-ms (2000..6000), while preserving the P86 default 2000ms. It renders 5.5s of the exact same held original public SoundFont Spec Test note59, velocity100 on 44.1kHz stereo native 86Box EMU8000, baseline versus gated P208 converter candidate.

Test requires equal first 2s PCM, only two changed driver register series ATKHLD/DCYSUS, >1000 genuinely different later stereo frames, and first changed frame between 2.6 and 4.1s, not in attack. Independent negative mutations reject early difference, missing late effect and isolated single-sample change. Only numerical evidence uploaded; raw ROM, SF2, WAV and traces remain ephemeral.

The original Creative driver reference comes from successful P207 original Win95 SBAWE.VXD (virtual AWE64). The actual CT4390 physical AWE64 silicon Hold/Decay behavior and 0x0C attack remain NOT MEASURED by this P209 test. No production DSP change; no release approval.

## Actual completed Windows/Linux research runner evidence – 9 November 2026

- Exact product-UNCHANGED research commit: `76c4db2ed2d4d687ae2e4ab9a8a384fc77988335`.
- GitHub Actions [P209 #42714876752](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42714876752) **completed SUCCESS**; dedicated artifact `P209-Native-EMU8000-Late-Phase-PCM-Evidence` ID `13717402266` inspected.
- Both native 86Box-derived chip renderers produced **242,550 frames** of 44.1-kHz, stereo PCM16, source SF2 public original spec v3.0 Bank0/Program0/Note59 Velocity100.
- First 2s PCM exactly equal; indeed **0 changed frames in 0..3 seconds**. **First changed stereo PCM frame = 132485 = 3.004195s**.
- Total 110,056 differing stereo frames across 5.5s. Specifically 43,911 differences during seconds 3..4 and 44,095 during seconds 4..5.
- Register series change isolated to ATKHLD/DCYSUS; original P207 register comparison preserved and IP remains 1 code unit off.
- Three deliberately faulty self-test cases were rejected (early difference, no late effect, one-frame glitch). A native real-chip A/B was executed, not just a formula.
- **Meaning:** P208 has a concrete LATE musical PCM consequence; this does NOT prove that the updated later waveform is closer to silicon. The original physical CT4390 81.85-cent EARLY attack mismatch remains untouched. No DAW/ASIO or independent FULL AUDIT; no release.
