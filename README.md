# 125A AWE Synthesizer
Windows x64 VST3 instrument project: historically faithful Sound Blaster AWE32/AWE64 EMU8000 synthesis.

**Current state: v0.1.0 source-import / audit baseline — NOT a VST3, NOT a build/release PASS.** No executable Windows VST3 exists in this repository yet.

- Development branch: `develop/v0.1.0-upstream-audit`. Keep `main` stable.
- A complete version-pinned *upstream source snapshot* (C and C++) is under `upstream/AWE32Emu/`; its original CMake console executable is preserved separately.
- The upstream snapshot is from [turican0/AWE32Emu](https://github.com/turican0/AWE32Emu), exact commit `17b0578fe59909dfaa784b5531d6d1a3a80729ce` (2026-10-21). It contains the modified [86Box](https://github.com/86Box/86Box) EMU8000 core.
- Original Creative ROMs, SoundFonts, DOS/Windows drivers, game samples and recordings must never be committed or included in public CI artifacts.
- Steinberg **VST3 SDK 3.8.1**, native **C++23** for new 125A VST3 code, Windows x64 only; keep upstream original 86Box C core in C and original CLI target C++17 for controlled baseline comparison.
- 86Box chip's native playback timing is **44,100 Hz**. Arbitrary VST3 host sample rates require a correctly implemented and measured sample-rate conversion strategy, not changed chip constants.
- License/attribution and release boundaries: [docs/PROVENANCE-AND-LICENSES.md](docs/PROVENANCE-AND-LICENSES.md).
- Audit findings and required tests: [docs/AUDIT-ENTRY-2026-10-31.md](docs/AUDIT-ENTRY-2026-10-31.md).

## Source baseline (optional console executable)

```sh
cmake -S . -B build -D125A_BUILD_UPSTREAM_CLI=ON
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

This only attempts to compile the **upstream console renderer**, not the planned VST3. No Windows/DAW or ROM-backed test results have been claimed. The ROM `awe32.raw` and ROM preset description (`SYNTHGM.SF2` or `1mgm.sf2`) are user-supplied runtime fixtures only.

## Mandatory engineering guidance

Before development read `challanger2000/125A-Engineering/START-HERE.md` in its specified order and apply the relevant engineering standards and QA gates. For GUI work also read `challanger2000/125A-Branding` and its approved master assets.
