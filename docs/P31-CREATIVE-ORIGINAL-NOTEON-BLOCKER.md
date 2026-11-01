# P31 — Original Creative DOS SF2LIB note-on test against the user's bank
2026-11-01 — **RESEARCH ONLY; NOT A VALID ORACLE YET**

## Goal and actual experiment

Run actual Creative ADIP 3.01 DOS demo linked against the original Creative library, after loading the user's SoundFont, with these exact MIDI events:

| Event | Value |
|---|---|
| Bank | 0 |
| Program | 000 and 007 (each in a fresh emulator process) |
| Note | C3 / MIDI 48 |
| Velocity | 100 |
| ROM | **actual user-provided** 1,048,576-byte `awe32.raw` (not public) |
| SoundFont | actual `Synth 512 Bank.sf2` (555,754 bytes; never committed) |

The DOS demo has no automated program-change/note-on command-line switch. The isolated local research script `tools/p31_private_demo_noteon_patch.py` verifies the exact original `DEMO.EXE` SHA256 (`49bcb8ad27ba24bf021b7697a924595da8846666a218a8b56440dff2207db647`), then produces **private, never-distributed** copies that send the requested MIDI program and note after Creative init/load.

The script changes only the demo's keyboard-input call sites, bank/program/note/velocity immediates, and the subsequent 2-second wait. It does **not** alter the original Creative library's internal SF2 parsing or MIDI code. These are **instrumented original-program** experiments, NOT unmodified binary execution.

DOSBox-X 2026.10.01, Linux SDL2 x64, `-debug -log-con`, actual wave ROM in `[emu8k]`, 8192 KiB emulated AWE32 DRAM. The original 2.01 bank is refused by the 1996 SDK; a *private temporary bank copy* differs only in `INFO/ifil` minor 1->0. The original remains intact.

## Actual observations

| Test | Emulator note-voice debug records | Sample memory addresses used |
|---|---:|---|
| Creative original, bank 2.00-header copy, program 000 | **16** | All `src=ROM`, start ~`0x016EA1`, loop zero |
| Creative original, same copy, program 007 | **16** | All `src=ROM`, start ~`0x016E98`–`0x016EA7`, loop zero |
| Creative original, synthetic valid-looking 2.00 `TINY200.SF2` with PCM sample, program 000 | **16** | All `src=ROM`, start ~`0x016173`–`0x016182`, loop zero |
| Creative original, bundled DOS `SYNTHGM.SF2` (2.00), program 000 | **0** debug records with current auto-note setup | none |
| 125A P26 real user-bank program 000 | **2** | `CCCA = 0x23F8CA` (~RAM) |
| 125A P26 real user-bank program 007 | **4** | `CCCA = 0x23EFE9` (~RAM) |

During these runs, DOSBox-X's `EMU8000: RAM load` messages reported only one word at `0x200000`. This is **not sufficient** to establish a successful upload of the user's ~261k sample words to emulated DRAM.

A trial using DOSBox-X's `DX-CAPTURE` command and the modified program 000 produced a 48000 Hz stereo capture of ~17.5 s whose audio channels were all zero (`peak = 0`). The debug `EMU8000: note voice` messages alone therefore do **not** prove that the source patch is successfully playing the intended samples. Emulated 1996 library guest and emulator behavior, SoundFont 2.00 version-only compatibility, bank selection and note-generation must be validated separately.

**Strong mismatch:** The original SDK experiment is triggering/starting 16 ROM voices with invalid loop addresses (or initialization events misinterpreted as note-on), not the 2/4 sample-RAM layers that our actual SoundFont definition selects. This test cannot serve as a valid register-value or audio reference for either bass program.

## Important finding and decision

**Do not modify production SF2 generator conversion, chip DSP, filter, FX or voice allocation to mimic these failed DOS traces.** The experiment is diagnostically invalid until a correctly functioning Creative library+guest produces the expected bank layers and audible PCM. Previous P30 statement "user bank loaded" meant the DOS application reached its key loop after its SF2 loader call returned; it did *not* establish loaded playable samples. This is a correction to that inference.

The better established reference is the original AWE32Emu project's **Win95 VxD running in an instrumented 86Box guest**. The upstream documentation `upstream/AWE32Emu/docs/TESTING.md` reports 10/10 Win95/DOS/SDK register comparisons on its own valid GM/SF1/SF2 banks; these have not been independently repeated for our two presets. An exact user-bank test still requires a validated original Creative guest driver that accepts the SoundFont and yields 2/4 real sample layers, then event trace comparison.

Local/private artifacts (original SDK EXE, patched derivatives, ROM, SF2, WAV) remain uncommitted. This repository only carries source for the test patch and this report. The commercial/private VST3 runtime and the P26 audio path are unchanged.

**Bottom line:** Original Creative code was *executed*, but original-Creative 000/007 register parity has **NOT** been established. P26 remains the newest verified user-bank audio correction.
