# P08 — EMU8000 project-recalled ROM/SF2 paths

**Status: candidate, verify actual Windows CI before acceptance.**

The VST3 processor/controller now serialize version **2** state with Program,
ROM pathname, SF2 pathname and explicit asset-path flag. Stored paths are
UTF-8 strings with a 4096-byte bound, never embedded ROM/SF2 audio data.
Legacy version **1** (magic/version/program) remains supported; old projects
will use the default local asset configuration.

New plugin instances can read one local plain-text file:

  %APPDATA%\125A\AWE Synthesizer\assets.cfg

Example:
  ROM=C:\Emulation\awe32.raw
  SF2=C:\SoundFonts\Synth 512 Bank.sf2

Double quotes around paths with spaces are supported. If that config is
missing, the previous AWE32_ROM_PATH and AWE32_SF2_PATH environment
variables remain compatible fallbacks. Config and ROM/SF2 disk reads are
limited to setActive/getState control lifecycle, never the audio callback.
A config typo is not silently accepted, and the parse is transactional.

Tests verify: V1 backward compatibility; V2 path/program roundtrip; all
truncated states fail without partial state changes; malformed version,
invalid Program and oversized paths; Windows-style config parsing and
invalid-config rollback.

**Still NOT RUN / NOT IMPLEMENTED**
- GUI browse buttons; this config is an interim file selection mechanism.
- Full Studio One save-close-reopen with an actual ROM and SF2.
- Visible error/relink dialog for missing or moved asset files.
- Active-host setState will update Program, but changed asset file paths
  take effect on the next deactivate/activate cycle, not inside process().
