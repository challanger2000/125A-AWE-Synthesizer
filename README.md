# 125A AWE Synthesizer
Windows x64 VST3 instrument project: historically faithful Sound Blaster AWE32/AWE64 EMU8000 synthesis.

**Current state: v0.1.0 experimental Windows VST3 developer build, Steinberg Validator 47/47, native tests 6/6 (Windows Actions #41234357310). NOT approved or tested in Studio One.** P08 adds versioned asset-path project recall; this change requires its own CI evidence.

- Development branch: `develop/v0.1.0-upstream-audit`. Keep `main` stable.
- A complete version-pinned *upstream source snapshot* (C and C++) is under `upstream/AWE32Emu/`; its original CMake console executable is preserved separately.
- The upstream snapshot is from [turican0/AWE32Emu](https://github.com/turican0/AWE32Emu), exact commit `17b0578fe59909dfaa784b5531d6d1a3a80729ce` (2026-10-21). It contains the modified [86Box](https://github.com/86Box/86Box) EMU8000 core.
- Original Creative ROMs, SoundFonts, DOS/Windows drivers, game samples and recordings must never be committed or included in public CI artifacts.
- Steinberg **VST3 SDK 3.8.1**, native **C++23** for new 125A VST3 code, Windows x64 only; keep upstream original 86Box C core in C and original CLI target C++17 for controlled baseline comparison.
- 86Box chip's native playback timing is **44,100 Hz**. The active native layer now supports streaming 44.1/48/96 kHz sample-rate conversion without per-block heap allocation (tested using a synthetic sine instrument), but VST3 host latency integration and reference-chip sound parity remain open.
- License/attribution and release boundaries: [docs/PROVENANCE-AND-LICENSES.md](docs/PROVENANCE-AND-LICENSES.md).
- Audit findings and required tests: [docs/AUDIT-ENTRY-2026-10-31.md](docs/AUDIT-ENTRY-2026-10-31.md).

## Source baseline (optional console executable)

```sh
cmake -S . -B build -D125A_BUILD_UPSTREAM_CLI=ON
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

This only attempts to compile the **upstream console renderer**, not the planned VST3. No Windows/DAW or ROM-backed test results have been claimed. The ROM `awe32.raw` and ROM preset description (`SYNTHGM.SF2` or `1mgm.sf2`) are user-supplied runtime fixtures only.

## Active native engine (Windows x64)

The active code under `src/engine/` integrates `Synth`, `SoundFont`, the original-model `Emu8000Core`, and an isolated patched 86Box-compatible `EMU8000` C renderer. The pinned upstream snapshot under `upstream/` is untouched. For validation:

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 -D125A_BUILD_ENGINE_PROBES=ON
cmake --build build --config Release --parallel 2
ctest --test-dir build -C Release --output-on-failure
```

Current native coverage: source provenance, 86Box chip initialization and bounded FIFO/queue, SoundFont zone selection, 44.1/48/96 kHz block-partition equivalence with a synthetic MIDI instrument, **plus separate 86Box chip FIFO/44.1/48 kHz synthetic waveform tests**. **Authentic EMU8000 ROM/SF2 sonic parity, VST3 processor/controller, project recall, validator and Studio One tests are not yet complete.**

See [docs/AWE-P05-RENDER-RESAMPLER.md](docs/AWE-P05-RENDER-RESAMPLER.md) for audit boundaries.

## Mandatory engineering guidance

Before development read `challanger2000/125A-Engineering/START-HERE.md` in its specified order and apply the relevant engineering standards and QA gates. For GUI work also read `challanger2000/125A-Branding` and its approved master assets.
