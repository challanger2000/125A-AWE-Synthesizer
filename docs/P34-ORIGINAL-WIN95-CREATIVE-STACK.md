# P34 — Authentic Creative Windows-95 SoundFont driver stack audit

**Date:** 2026-11-01. **Status:** Static evidence complete; Win95 **execution with user's SF2 not performed**. This is research and does **not** alter the current P26/P27 sound or commercial VST3.

## Question

Which actual original Windows-95 components load and interpret an SF2 bank before the EMU8000 receives MIDI note-on register writes?

We must not infer SoundFont v2.01 preset offsets from **SF1 bank** tests or from the DOS SDK, and must not change the P26 audio because of a hypothetical "Creative fill" behavior.

## Examined original, hash-verified Creative ADIP 3.01 binaries

The CI audit `tools/p34_creative_win95_binary_audit.py` independently downloads the **exact** public-mirror files, verifies each original Git blob SHA1, inspects file format and imports/exports and scans technical RIFF/SoundFont markers. Proprietary binaries are not stored as GitHub source or in the published audit artifact.

| Component | Bytes | Executable format | Verified markers | Key role |
| --- | ---: | --- | --- | --- |
| `WINDOWS/DLL/AWEMAN32.DLL` | 35,840 | PE / Win32 | No `ifil,pgen,igen` marker; exports `AWEManager`, `AWEGetObject32`, `AWEGetObject16`, `AWESetObject16` | Windows API manager / bridge |
| `WINDOWS/DRV/WIN95/SBAWE.VXD` | 85,918 | LE (VxD) | `sfbk`, `ifil`, `phdr`, `pbag`, `pgen`, `igen` | Ring-0, hardware/driver stack; SF2 structural evidence |
| `WINDOWS/DRV/WIN95/SBAWE32.DRV` | 44,176 | NE (16-bit Windows driver) | `.sbk`, `.sf2`, `sfbk`, `ifil`, `pgen`, `igen` | Windows multimedia driver with SF2-related data/strings |

**Source-level chain independently confirmed:** The original Creative `WINDOWS/SAMPLE/AWEDEMO/WINAWE32.C` dynamically loads `AWEMAN32.DLL` then calls `AWE_LOAD_USER_BANK` and `AWE_SEND_MIDI`. The manager has no obvious `pdta` SoundFont header markers; the NE and LE driver files do. These are static observations, **not** a formal proof of exactly which binary performs each SF2 arithmetic operation.

Source: <https://github.com/qb40/sound-blaster-awe32>. Exact original blob hashes in audit JSON.

## Original trace prerequisite (not supplied by P31)

An executable Win95 guest must include **the full matching original** `AWEMAN32.DLL`, `SBAWE32.DRV`, `SBAWE.VXD`, 86Box instrumented EMU8000 ISA reads/writes and the user's original bank. The guest image is proprietary and **not published** by upstream and is **not present** in this research environment.

Previous P31 DOS demo under DOSBox-X is not a replacement for the Win95 test: it rejected SF2 v2.01, and private temporary version-2.00 copies produced 16 invalid ROM voices, not the 2/4 sample-RAM voices. Never use those traces to update audio code.

## New strict comparison gate

`tools/p34_validate_win95_sf2_noteon.py` accepts the two recorded ISA traces for *one* program, and:

1. Parses pointer + register writes, including 32-bit `CCCA`, per voice.
2. Requires a plausible real SF2-RAM note-on (not a 16-ROM initialization or error artifact).
3. Rejects mismatched voice counts: **program 000 → exactly 2 layers**, **program 007 → exactly 4** (at MIDI note 48 / velocity 100).
4. Only then compares the effective note-on register values (`IP`, `IFATN`, `ENVVOL`, `ATKHLDV`, `DCYSUSV`, `LFO1VAL`, `CSL^`, etc.), pairing by pitch rather than absolute voice ID.
5. Treats DRAM base/address allocation differences as separate diagnostics, not automatically as SF2 parameter errors.

A **synthetic self-test** verifies success on two valid RAM note-ons and rejection of 16 ROM starts/wrong layer count. It is NOT a live Win95 trace parity test.

Example (only once genuine guest trace is available):

```bash
python tools/p34_validate_win95_sf2_noteon.py \
  --program 7 --ours P29_007_win95_noteon.trace \
  --original-win95 win95_guest_007.trace --out P34_007_diff.json
```

**Important:** Even if the validator gate passes, the trace provenance must be independently confirmed; the tool cannot detect a fake file purporting to be a Win95 capture.

## Verdict

- **VERIFIED:** original Win95 AWE32 uses a mixed Win32-manager / NE-multimedia-driver / LE-VxD stack, and both driver executables contain SoundFont file-structure identifiers; the Win32 manager exports `AWEManager`.
- **VERIFIED:** P33 audio changes significantly under the two SF2 generator interpretations; this is a real effect of parameter composition, not proof that either version matches historical Creative Windows 95.
- **NOT VERIFIED:** Which SF2 v2.01 preset-generator precedence the original Win95 driver *actually applies* to the user's bank. Original DOS SF2LIB has distinct behavior/version requirements and is not an authority for the Win95 stack.
- **NOT RUN:** Windows 95 guest, genuine original-Creative 000/007 note-on trace, full hardware line-out comparison.
- **NO production changes** to `SoundFont.cpp`, DSP, VST3, GUI, ROM handling or the already verified P26 audio.

**Do not claim 1:1 hardware audio or revert P26 based on these static observations.**
