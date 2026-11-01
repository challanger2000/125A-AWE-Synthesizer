# P29 – Original Creative drivers: executable reference vs VST3 runtime

**Status:** source/architecture feasibility evaluated, note-on port-trace exporter implemented on this research branch. Original Creative driver has **not** been run with the private Synth 512 Bank yet; no exact-match claim.

## Concrete original Creative code and what it is

The Creative **Sound Blaster AWE32 Developer Information Package 3.01** (2 August 1996) contains actual binaries:

| Artifact in `qb40/sound-blaster-awe32` | Function | Host/runtime |
|---|---|---|
| `DOS/LIB/SF2LIB/FLAT/PAWE32.LIB` (47,616 bytes) | Original 32-bit x86 *SF2* DOS routines; `awe32SetPresets`, `awe32NoteOn`, `awe32RegW/DW` | 32-bit DOS extender (sample `DOS/DEMO/HCMAKE` uses MetaWare High C / Phar Lap) |
| `DOS/DEMO/DEMO.C` | Source example for SoundFont load (stream samples then set presets), MIDI-to-API calls, device I/O | DOS / protected-mode extender |
| `DOS/LIB/SF2LIB/INCLUDE/CTAWEAPI.H` | Original API declarations and data structures | DOS ABI; direct EMU8000 I/O |
| `WINDOWS/DRV/WIN95/SBAWE.VXD` (85,918 bytes) | Win95 VxD device-side low-level Creative logic | Windows 9x VMM and x86 system services |
| `WINDOWS/DRV/WIN95/SBAWE32.DRV` (44,176 bytes) | Win95 multimedia driver-side interface | Win95 subsystem |
| `WINDOWS/DLL/AWEMAN32.DLL` (35,840 bytes) | Windows resource / SoundFont management | Legacy Windows driver stack |

Verified source: https://github.com/qb40/sound-blaster-awe32 ; read the Creative README license before using any binaries. The license **restricts copying, distributing and derivative works**. The SDK being mirrored publicly does not make it an open-source dependency for a Gumroad VST3. We do NOT copy, embed, or distribute those files in this repository or any product package. Exact permissions for a private research runtime and any distribution require separate review.

**These are computer-side drivers/libraries, not firmware executed by a CPU inside the EMU8000.** The EMU8000 is the register-controlled wavetable chip and `awe32.raw` is a wave *sample* ROM. Loading drivers into the plugin does not, by itself, make the chip DSP more accurate.

## Practical architecture decision

1. **Keep inside the real-time VST3:** 125A's bounded/instance-local MIDI -> EMU8000 register translation plus the measured 86Box-derived chip DSP. No DOS/Win95 VM or executable Creative driver inside the DAW's audio callback. Sample accuracy, CPU, host crash isolation and private-ROM handling remain manageable.
2. **Run separately as research reference:** Original 32-bit `SF2LIB` inside a DOS/x86 environment with an instrumented AWE32 ISA port backend (modified 86Box VM in the source project's `sources/ref86box`). This can produce original Creative SDK note-on port traces without any physical AWE32. For a native Windows 95 reference, run matching `SBAWE.VXD` in a Win95 guest instead: **SDK and VxD are different driver families and their register sequences are not interchangeable.**
3. **Compare note-on register values** for bank 0, programs 000 and 007, C3/48, velocity 100, same SoundFont, initial state and MIDI CC. Compare decoded register value sets at voice starts rather than raw timestamps, allocation order or initialization sequence. The original project already has a `tests/notes_diff.py` reference tool in branch `sources`: https://github.com/turican0/AWE32Emu/blob/sources/tests/notes_diff.py .
4. **On verified mismatches:** repair only the isolated 125A SF2 parameter conversion (e.g. preset default+offset logic fixed in P26), add targeted synthetic regression and rerun full native/VST3 tests. Don't adjust chip tone to match unrelated FluidSynth.
5. **Hardware audio verification** is a separate level: the original project's measured 86Box chip source was calibrated against AWETEST from a real AWE32. Original-driver register parity says nothing by itself about the analog audio output; physical-card measurements remain the standard for the chip level.

## Implemented on P29 branch

`tools/sf2_timbre_probe.cpp` supports two optional command-line switches:

```text
awe32_sf2_timbre_probe.exe --driver sdk --port-trace yes
awe32_sf2_timbre_probe.exe --driver win95 --port-trace yes
```

- Defaults remain `--driver win95 --port-trace no`, preserving the P25/P26 baseline behavior.
- Existing `assets.cfg` resolves user ROM+SF2, without copying or committing these files.
- Both captures use programs 000 and 007, note 48, velocity 100.
- The new `*_sdk_noteon.trace` or `*_win95_noteon.trace` contains the **actual 125A engine's port writes** after bank load/initialization. This is NOT an original Creative driver's trace until compared with a separate real-driver VM run.
- This is offline-only instrumentation, not a realtime DAW feature; the VST3 signal path and chip are unchanged.
- On first run with the original SF2LIB: use the `sdk` mode only. It will not prove that the Win95/VxD mode matches.

## Remaining blockers for a real SDK comparison

- A configured DOS/x86 guest/loader and instrumented ISA-port backend (the upstream VM/BIOS/guest images are intentionally not published).
- Building/loading Creative's original `SF2LIB` binary with a DOS extender and an **unmodified** test program, OR an SDK-compatible test harness in that guest; validate that the SDK parses `Synth 512 Bank.sf2` before comparing.
- Run the original SDK program changes and notes, capture register trace, compare against our new SDK trace. A mismatch is concrete evidence; a match is driver parity only.
- No attempt to run `SBAWE.VXD` directly in a 64-bit VST3: it relies on the Windows 9x VMM and isn't a freestanding firmware image.

## Technical sources

- Creative official EMU8000 Programmer's Guide: https://www.phatcode.net/res/244/files/emu8kpgm.pdf
- Creative ADIP 3.01 repository and license: https://github.com/qb40/sound-blaster-awe32/blob/master/README.TXT
- Original project's real-driver trace methodology: `upstream/AWE32Emu/docs/TESTING.md`, upstream `sources/ref86box`
- Real-chip calibration: `upstream/AWE32Emu/docs/re-notes/emu8000_tuning.md`

**Conclusion:** Original Creative software is usable as an **external executable oracle**, not as a drop-in 125A x64 VST3 component. That is an actionable, narrower route to authentic SF2 parameter handling, without shipping copyrighted binaries or compromising low-latency audio.
