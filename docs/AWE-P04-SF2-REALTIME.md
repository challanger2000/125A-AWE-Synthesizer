# AWE-P04 — bounded SoundFont/MIDI NoteOn selection

**Status: native test PASS (Windows #41231977541); full VST3 / hardware parity still unverified.**

Upstream remains preserved byte-for-byte under `upstream/AWE32Emu/`.
The active selection/Synth copies are in `src/engine/`.

## Scope
- The original public `Bank::Select` is retained for historical parity/testing; its production replacement, `Bank::SelectInto`, takes caller-owned `std::span<Region>` and performs no heap allocation.
- Both APIs use the same zone enumeration and SF1-specific attenuation logic to prevent algorithm drift.
- Active `Synth::NoteOn` uses a per-instance fixed `std::array` of 64 regions. `StartLayers` uses fixed arrays for VoiceParams and DOS/SDK voice indices.
- A zone stack exceeding 64 matching regions is *rejected as a complete note*, not truncated and played incorrectly. `RegionOverflowCount()` exposes the count. This is a provisional safe bound, not a guarantee of compatibility with every arbitrary SF2; this policy must be reviewed before release.
- Native regression compares all emitted layers against the old selection algorithm, tests key/velocity/bank fallback behavior, capacity overflow, SF1 and SF2 generator merging, and instruments global heap allocation during the selection call.

## Boundaries
- The active Synth.cpp is now compiled and linked with Emu8000Core and 86Box chip code in `awe32_chip_safety` (P05). Native MIDI fallback and 44.1/48/96 kHz render tests pass.
- RenderBlock allocation issues originally listed here have been addressed in P05 for the tested paths. Audio-thread bank uploads, arbitrary real-time register writes, and error/log paths need separate audits.
- No audible hardware parity, VST3 host validation or Studio One test has been done for this patch.
- The fixed region limit, oversized preset behavior, absence of other audio-thread allocations, and all-bank loading are pending full end-to-end QA.
