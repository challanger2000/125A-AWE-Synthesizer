# 125A AWE Synthesizer
Windows x64 VST3 instrument project: historically faithful Sound Blaster AWE32/AWE64 EMU8000 synthesis.

**Current state: v0.1.0 experimental Windows VST3. P13 Windows Actions #41241525870 SUCCESS (12/12 native CTests); 47/47 Steinberg Validator reported. Owner confirmed earlier SF2 and Yamaha OPL3 playback in Studio One. Creative CQM, P14 VSTGUI editor and original-hardware parity need independent Studio One checks.**

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

## P12: Real YMF262 rhythm hardware with user percussion IBK

If you have a valid original **rhythm-style** Sound Blaster .IBK percussion
bank (same 3204-byte format as melodic IBK), append this line to the
existing Windows asset configuration:

    OPL3_DRUM_IBK = "C:\SoundBlaster\YourDrumBank.IBK"

Both IBK files are optional; neither is redistributed. Restart/re-activate
the VST3 after changing asset paths. Hardware=Yamaha OPL3, MIDI channel 10
(zero-based channel 9) selects the drum patch by MIDI note. The bank's
IBK percussion-voice byte 11 must identify one of the actual YMF262 hardware
drums: 6=BD, 7=SD, 8=Tom, 9=Top Cymbal, 10=Hi-Hat. Unmapped notes
stay unmapped: we do not invent a GM-to-drum translation.

Register 0xBD rhythm mode (bit 5) controls five original key bits:
BD=bit4, SD=bit3, Tom=bit2, Cymbal=bit1, HH=bit0. The chip uses
operators on YMF262 channels 6/7/8, leaving **15 melodic voices** instead
of 18 while a drum bank is active. Only the corresponding original chip
operators are programmed, preserving shared-channel frequency behavior.
One physical drum voice retriggers rather than spawning extra voices.

P12 state V5 adds a persisted external drum-IBK path; state V1-V4 remains
readable. No Creative ROM, samples, drivers or bank binaries are bundled.
If an explicitly configured IBK is invalid, FM remains silent until
configuration is corrected and plugin reactivation. Without a percussion
bank P11 behavior (18 melodic voices) remains unchanged.

**Still unverified:** Studio One playback with a real licensed percussion
IBK, Creative Windows/DOS driver-to-GM rhythm mapping, actual YMF262
hardware PCM parity, Creative CQM and Live!/EMU10K1.

## P13 — genuine Creative CQM hardware mode (experimental)

New selectable **Hardware** modes in the generic host editor:
EMU8000 AWE32/64 (0), Yamaha OPL3 (1), Creative CQM (2).

Creative CQM uses the entirely separate **Nuked CQM 0.9 beta** emulator,
pinned verbatim to upstream commit `274a4c463ab2f8e193b1c1192f9d4e0d02df521a`
under `third_party/Nuked-CQM/`, with its original LGPL-2.1-or-later
copyright and license. This is real Creative Quadratic Modulation, **not**
a Yamaha-OPL3 sound with a different label. The existing 125A MIDI and IBK
translation layer writes authentic register parameters to the *selected*
emulated FM chip, either CQM or OPL3. The same optional melodic IBK path is used by both chips; none are bundled.
**Nuked CQM 0.9 beta rhythm-mode PCM failed our synthetic regression**,
so this release deliberately **does not enable CQM percussion**. Channel
10 stays silent on CQM, whereas authentic 0xBD hardware drums remain
implemented for Yamaha OPL3 with its own verified drum-IBK path. No new file UI.

The VST3 state moves to V6, extending the saved engine enumeration to 2.
V1-V5 project states remain readable and default/preserve prior engine values.
Audio is delayed to the existing EMU8000-reported latency (unchanged to DAW
PDC), with no allocations inside the process callback.

Nuked CQM currently calls its own engine **0.9 beta**. It needs a real
Creative CQM card comparison before declaring verified AWE64 parity.
The 86Box docs confirm CQM emulation via Nuked CQM on supported cards;
**AWE64-specific silicon verification and custom GUI remain open**.

## P14 — functional VSTGUI test editor (development)

This lightweight, fixed-size VSTGUI editor replaces the host's generic editor
with two **real** VST3 parameter selectors: **Hardware** (EMU8000 AWE32/AWE64,
Yamaha OPL3, Creative CQM) and **Program** (0..127). Both are bound to the
existing processor parameters 1001 and 1000, respectively. P14 fixes the
controller's three-way Hardware recall normalization (0, 0.5, 1); previous
saved project values keep their V6 format and parameter IDs.

It deliberately does not add unsupported ADSR controls, a fake SF2 bank
browser or a designer faceplate. User-provided ROM, SF2 and IBK paths still
come from `%APPDATA%\\125A\\AWE Synthesizer\\assets.cfg`. Change the
configuration and re-activate/reload the plugin to load a different bank.
Existing engine DSP and CQM percussion limitations remain unchanged.

**Validation:** `125A_p14_vstgui_contract` is a static XML/CMake/controller
binding check only. A Windows VST3 build, validator, packaged-editor
attach/detach, mouse/automation and Studio One project-recall tests must be
reported independently. P14 is **DEV** until these have run.

### P14 follow-up — real Program menu (owner Studio One feedback)

The owner verified the P14 editor opens, the Hardware selector works, and
all three engines output sound, but **Program selection was not usable** and
only a single timbre was heard. Replace the generic numeric Program
parameter with a proper **128-entry VST3 StringListParameter** (displaying
`000` through `127`), so VSTGUI's `COptionMenu` has explicit choices.
Keep the original parameter ID 1000, normalized 0..127 mapping, project
persistence, processor event path and existing synth DSP unchanged.

**A Program choice does not create sounds without loaded patches.**
Yamaha OPL3 and Creative CQM deliberately use the single developer
test patch if `OPL3_IBK` has not been configured. Both need a genuine
melodic IBK to make Program 0..127 select different FM patches.
EMU8000 requires an SF2 containing those presets; a missing program
can map to bank 0/preset 0 per the current emulated driver behavior.
No licensed SF2 or IBK data is included in CI/artifacts.

Status: source contract only until new Windows VST3 build and owner
Studio One tests. Verify the menu opens, shows `000`..`127`, selecting
`001` changes the host Program parameter, and that playing a note
changes timbre when a suitable multi-preset bank is actually loaded.

## P15 DEV: built-in 125A FM presets (no external IBK needed)

The plugin now creates an **independently authored 125A bank of 128
distinct 2-operator YMF262-register patches** at activation and uses it for
both Yamaha OPL3 and Creative CQM. The Program selector chooses among these
register patches without a file. This is **not** a dump of Creative's original
GM factory patch bank, and the names/numbers do not claim authentic Creative
GM timbres. These are actual register-level FM sounds, not samples or simulated
waveforms. A genuine user-provided melodic \`OPL3_IBK\` still replaces the
internal bank if explicitly configured.

Yamaha OPL3 additionally activates the genuine five-lane YMF262 percussion
mode with 125A-authored register patches for GM MIDI channel 10. The five
physical rhythm instruments are bass drum, snare, tom, cymbal and hi-hat;
many GM percussion notes must share these voices. Creative CQM 0.9-beta
percussion remains disabled because the actual emulation does not have verified
rhythm PCM. A valid user \`OPL3_DRUM_IBK\` overrides Yamaha's built-in drum
bank. An invalid explicitly requested bank retains the existing fail-closed
behavior (no misleading fallback pretending that file was loaded).

**EMU8000 assets remain different:** \`SF2\` is still user-supplied. The
original **Creative EMU8000 sample ROM** is proprietary and is **not bundled**
in the public repository or public Windows artifact. An authorized external
ROM can continue to be configured with \`ROM\`. An internally authored OPL3
register bank cannot replace the EMU8000 sampled waveform ROM.

P15 native regression covers the 128 unique register records, separate
OPL3/CQM PCM for different programs, Yamaha rhythm PCM and CQM rhythm exclusion.
This is a development candidate pending a passing Windows CI and owner
Studio One test. Existing VST3 controller IDs and V6 project-state serialization
remain unchanged.
