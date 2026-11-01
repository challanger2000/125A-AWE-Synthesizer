# P30 — Original Creative DOS SF2LIB executed with the user's own AWE32 wave ROM

**Date:** 2026-11-01. **Scope:** private local research. No proprietary ROM, private SoundFont, original Creative executable, or original SF2 bank is added to source control.

## Actual original binary

- Creative ADIP 3.01 (2 August 1996), `DOS/DEMO/DEMO.EXE`, Git blob `e10b8705c6a46444a998c4f6aa74a1cda2081506`.
- DOSBox-X from official project GitHub Linux nightly (2026-10-31, version 2026.10.01).
- **Actual original, user-provided** `awe32.raw` (1,048,576 bytes), kept local only.
- `[sblaster] sbtype=awe32`; **`[emu8k] rompath=/.../awe32.raw` and `memsize=8192`** (ROM must be configured in `[emu8k]`, not `[sblaster]`).
- Guest `BLASTER=A220 I7 D1 H5 P330 T6 E620`.
- The original Creative DEMO source `DOS/DEMO/DEMO.C` actually scans command-line **`/SBK:`**, even though its usage printed for the SF2 variant says `/SF2:`. All explicit-bank tests use `/SBK:FILENAME.SF2`.

## Real, reproducible original-binary results

| Input bank | `ifil` | ROM backend | Result at original Creative DOS program |
|---|---|---|---|
| SDK `SYNTHGM.SF2` | 2.00 | actual | **Loaded**; program reaches `Press <Esc> to stop ...` |
| Synthetic 16,918-byte `TINY.SF2` with PCM sample | 2.01 | actual | **Rejected**: `ERROR: Cannot load SoundFont file TINY.SF2` |
| *Byte-identical* synthetic `TINY200.SF2`, except `INFO/ifil` minor 1→0 | 2.00 | actual | **Loaded**; reaches idle loop |
| User's 555,754-byte `Synth 512 Bank.sf2` (guest `BANK.SF2`) | 2.01 | actual | **Rejected**: `ERROR: Cannot load SoundFont file BANK.SF2` |
| User's `BANK200.SF2`, changed **only one byte** at file offset **34 (1-indexed)**: `INFO/ifil` 2.01→2.00 | 2.00 | actual | **Loaded**; reaches `Press <Esc> to stop ...` (loading takes longer, verified with 25-s run) |
| SDK GM bank + 22,050 Hz mono `TONE.WAV` test file | 2.00 | actual | **RAM WAV loading works**; menu displays `Press '1' for TONE.WAV` |

**Control:** Win2022 isolated emulated AWE32 with a dummy 1 MiB ROM recognized original Creative DOS executable but the SDK's user-bank error still required investigation. SB16 instead of AWE32 reported `ERROR: SB AWE32 not detected`. The full local experiment used user's authentic wave ROM.

### Exact byte-level proof

- Original user bank SHA-256: `d5b99ec38fddf59f53f66b90921e170d207bf3bbd73960f6e4175c39ef68349b`.
- Temporary SDK-v2.00-header copy SHA-256: `d1e365ae148d29308247d812fe71cd0ca016603f8add41ca8c969f90c1875ec5`.
- `cmp -l BANK.SF2 BANK200.SF2` reports **only byte 35 (1-indexed): 001 → 000**. All sample data, presets, instruments, modulation parameters, pan settings and sample headers remain unchanged. The source file was not modified.
- The synthetic PCM bank independently gives the same 2.01 reject / 2.00 load outcome. So the original SDK's behavior is not unique to the user's particular SoundFont.
- Version-only patch is **a compatibility experiment, not a full SF2 v2.01→2.00 semantic conversion**. Some newer format features may remain unsupported or differ; the resulting audio is NOT established as hardware-correct.

## Conclusions

1. **Proven:** Actual original Creative DOS SF2-library-based executable, with real EMU8000 wave ROM, **successfully loads the entire user's 512 KB SF2 bank** when its file version is presented as 2.00. It does not accept the original 2.01 file without that byte-level change. Real DRAM uploads are operational at least for the small WAV control.
2. **Not yet proven:** Original Creative note-on register sequence for 000 Grungy Ramp Bass / 007 TX81Z Lately Bass at note 48 velocity 100. The stock `DEMO.EXE` interactive loop only sends a note on keypress for extra WAV banks; the two user presets have **not** been triggered or captured from this original executable. The original SDK code has not been integrated into the VST3.
3. **Not proven:** full identical sound to physical AWE32; DOSBox-X is an emulator and the real-chip reference recordings are a separate evidence layer.
4. **Next exact oracle task:** Generate controlled program-change/note-on events using a DOS test harness **linked to the original Creative SF2LIB** (or a verified guest MPU-401 MIDI input technique) and capture EMU8000 ISA writes for programs 000 and 007. Compare those writes with `P29 --driver sdk --port-trace yes`. Do not modify P26/P27 chip DSP on speculation.

The original Creative package contains license restrictions; no SDK binaries are redistributed by 125A VST3.
