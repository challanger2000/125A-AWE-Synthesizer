# 125A AWE Synthesizer
Windows x64 VST3 instrument project: historically faithful Sound Blaster AWE32/AWE64 EMU8000 synthesis.

**Current state: v0.1.0 experimental Windows VST3; P10 Windows Actions #41238191358 SUCCESS (Steinberg Validator 47/47, 9/9 CTests). Owner confirmed SF2 and initial OPL3 FM audio in Studio One. Project save/reload and original-hardware sonic parity remain NOT RUN.**

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

## OPL3 register-core provenance (historical P09 milestone)

A separate, unmodified, version-pinned [Nuked OPL3](https://github.com/nukeykt/Nuked-OPL3) YMF262 register-level emulator is included under `third_party/Nuked-OPL3/` (commit `765ec962e473aeb767e4cba74ffdc8f588ffbfe8`, LGPL-2.1-or-later). `src/opl3/` builds its own native FM audio regression test by default. **Historical P09 stage only:** OPL3 originally had no VST3 MIDI route; P10 added a real two-operator Yamaha hardware mode. A real CQM is a distinct pending implementation, never silently substituted with Yamaha OPL3. EMU10K1/Live! remains future research.

The project now has a fixed **28 MiB EMU8000 sample-RAM default** (plus independent 1 MiB Wave ROM), without a redundant RAM selector. Generated >8 MiB SF2 test data is not checked in and is deleted after the test. Windows CI evidence and original-ROM/Studio-One verification must be reported separately.

## P10: preliminary Yamaha OPL3 MIDI mode (development only)

The VST3's **Hardware** parameter switches **EMU8000 AWE32/64** (existing
default) and **Yamaha OPL3** (separate authentic Nuked YMF262 register core).
In Yamaha mode MIDI notes are mapped to up to 18 two-operator voices with
key-on/key-off, bounded voice stealing and velocity applied to operator TL.
The immediate sound is a **temporary 2-operator test patch**, NOT the original
Creative or Yamaha GM instrument bank. The existing "Program" parameter is
the EMU8000 SF2 selection only: changing 0..127 does not select FM patches.

Hardware mode is persisted in VST3 state V3; V1 and V2 projects default to
EMU8000. The OPL3 engine aligns its output to the host-reported 86Box FIFO
latency, preventing a hidden engine-switch latency change. No original
Creative CQM, Live!/EMU10K1, FM bank browser, finished GUI or DAW/FM
end-to-end verification is claimed. These require separate work and evidence.

## P11: Original Sound Blaster IBK instrument-bank loader

The Yamaha OPL3 mode now accepts an **externally supplied 3204-byte
Creative Sound Blaster melodic .IBK bank**, with 128 original 16-byte FM
register patches and their nine-byte instrument names. The VST3's existing
host-native **Program** control (0..127) selects the corresponding historical
FM patch, rather than always playing the old single test tone. The byte-for-byte
YM262 register values, including mod/car ADSR/waveform/feedback, are applied
to real Nuked OPL3 operators. Carrier-level scaling preserves the original
patch KSL/TL value at full MIDI velocity.

**Set the optional bank file path** in the existing Windows configuration:

    %APPDATA%\125A\AWE Synthesizer\assets.cfg

Append one line (replace the example path with your own file):

    OPL3_IBK = "C:\SoundBlaster\YourMelodicBank.IBK"

Keep the existing ROM and SF2 lines unchanged. Restart/re-activate the
VST3 to pick up the newly selected bank; resource loading never runs on the
audio callback. The IBK path is included in VST3 project state V4, with V1/V2/V3
migration (prior ROM/SF2 paths, Programs and Hardware selections retained).
A missing/invalid configured IBK **silences FM instead of pretending** the
single developer test tone is the selected bank. Without any configured IBK,
the earlier developmental FM tone remains so existing P10 projects still sound.

**Scope limitation:** IBK here means a 128-program *melodic* OPL2/OPL3
two-operator bank. Original FM percussion/rhythm mode, authentic Creative
FM driver volume tables, four-operator FM instrument formats and a GUI bank
browser remain separate work. This does NOT claim original AWE64 CQM or
Live!/EMU10K1 emulation. Original Creative FM banks and ROMs are not
distributed with the repository or Windows Actions artifacts.
