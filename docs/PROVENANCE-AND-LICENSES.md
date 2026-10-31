# Upstream source provenance and distribution boundaries

## Pinned source

- Original project: https://github.com/turican0/AWE32Emu
- Repository main commit: `17b0578fe59909dfaa784b5531d6d1a3a80729ce` (2026-10-21, `fix string`).
- Complete included upstream C/C++ console sources and documentation are reproduced **unchanged** in `upstream/AWE32Emu/`, preserving original paths and notices. No original ROM/SoundFont, Creative driver executable or audio reference recording is included.
- 86Box component from 86Box/86Box: `upstream/AWE32Emu/AWE32Emu/src/86box/snd_emu8k.c` and accompanying headers. This is the AWE32Emu project's modified chip core, **GPL-2.0-or-later**; see `upstream/AWE32Emu/COPYING.GPL-2.0` and `upstream/AWE32Emu/AWE32Emu/src/86box/README.md`. Existing authors' credits and source notices must be kept.
- Other AWE32Emu source: the original project README says **license to be decided** as of the pinned revision. The 125A owner states that permission has been obtained to reuse this code. This declaration does not document the scope of third-party relicensing/redistribution rights. Record actual authorization terms before any customer binary and verify GPL compatibility for a derivative binary containing the 86Box chip.
- Steinberg VST3 SDK: planned separate dependency version 3.8.1, MIT; **not vendored yet**.
- GPL permits charging for software but carries source/redistribution obligations. Mark release licensing NOT VERIFIED until those obligations and the author's reuse grant have been checked together.

## Clean public repository rules

**NEVER COMMIT:**
`awe32.raw`, `1mgm.sf2`, `SYNTHGM.SF2`, `SYNTHGM.SBK`, ROM/OS images, Creative proprietary DOS/Windows executables, personal recordings, vendor sample libraries, private keys or test output containing copyrighted data.

These may be used locally by a user who lawfully possesses them, outside the source tree, through an explicit runtime asset loader. A copied public ROM dump is not proof of a redistribution license.

## Developer constraints

Only the version-pinned snapshot is authoritative for comparisons. Never change upstream code to silence a regression without recording a patch and validating before/after register traces and audio PCM. 125A adapter code must be C++23 and callback-safe. An upstream console renderer passing does not demonstrate realtime VST3 functionality.
