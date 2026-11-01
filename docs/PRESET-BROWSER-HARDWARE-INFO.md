# 125A AWE Synthesizer — Preset Browser and hardware identification

Owner-approved interaction direction: 2026-11-01. **SPECIFICATION ONLY; not yet implemented or host-tested.**
Authoritative implementation baseline: `develop/v0.1.0-upstream-audit`.
This document records required behavior before any GUI redesign; it does not assert that a working browser exists.

## Hardware selection must be self-explanatory

The selected hardware name must have an immediately visible, short German explanation
inside the plugin itself (below the HARDWARE selector or adjacent to its information control).
Do not hide the distinction exclusively in README, a tooltip, or a manual.
The same longer descriptions must be available in the preset browser's hardware header/help area.

Labels and user-facing explanations:

| Hardware | Short description (always visible when selected) | Expanded help |
| --- | --- | --- |
| **EMU8000 — AWE32/AWE64** | **Sample-Synthesizer mit Wave-ROM und SoundFonts (SF2).** | Creatives samplebasierter AWE-Klangerzeuger; ROM- und SoundFont-Instrumente statt FM. |
| **Yamaha OPL3** | **Originaler Yamaha-FM-Synthesizer für klassische Sound-Blaster-Klänge.** | FM-Klangerzeugung mit Yamaha-YMF262-Charakter; die Instrumente stammen aus der gewählten FM-Bank. |
| **Creative CQM** | **Creatives eigener, OPL3-kompatibler FM-Synthesizer.** | FM-Nachbildung von Creative auf bestimmten späteren Sound-Blaster-Karten. Die gleichen OPL3-kompatiblen Instrumentendaten können anders klingen als beim Yamaha-OPL3. |

**Do not** describe CQM as another SoundFont/sample-ROM synth, or claim all AWE32/64 cards
have the same FM hardware. Do not claim that the two FM engines have distinct preset banks
when the bundled configuration currently uses the same MAUIFM.IBK bank.

## Main editor

- The long numeric `COptionMenu` covering all 128 programs is only a developer placeholder.
  Replace it with one compact **PREV — current program number + real name — NEXT**
  selection and a **BROWSER** button.
- Hardware selector shows a context-dependent short explanation from the table above.
  This explanation changes as the hardware selection changes and is readable without opening
  the browser. A dedicated info control may show the expanded text.
- No manual per-preset file operations and no permanent 128-row popup for common browsing.
- Unknown preset names may show a neutral fallback such as `Program 042`, but only if
  metadata is genuinely absent. Never present a guessed GM name as the source name.

## Preset Browser

- One shared browser for EMU8000, Yamaha OPL3 and Creative CQM, with instrument names,
  bank selection, search/filter and keyboard/mouse navigation.
- **EMU8000:** enumerate the actual loaded SoundFont's `phdr` preset names, bank numbers and
  program numbers; distinguish different banks and drum kits. The current internal
  SoundFont parser already contains these fields. A GM name table must not silently
  override actual user SF2 names.
- **FM:** read the 128 instrument names embedded in `MAUIFM.IBK` (or the active user's
  overridden IBK). Both FM engines can display the same bank names while using their
  different emulation cores.
- Browser selection and PREV/NEXT must drive exactly the same existing VST3 Program ID
  `1000`. Hardware is VST3 parameter ID `1001`. Preserve old project compatibility.
- Multi-bank SF2 selection is **not implemented yet** in the existing 0..127 program
  control. Design and implement a separate bank parameter/state mapping with migration
  and recall tests before claiming multi-bank support.
- The selected browser entry, current name and relevant hardware explanation must remain
  synchronized after automation, program change, project reload and changing engines.
- One new keypress after choosing a program must use the newly selected instrument;
  avoid stale FM release tails masking preview results.

## Acceptance and evidence

1. **NOT RUN:** Hardware selector changes the short explanatory text immediately,
   correctly on first editor open and after project recall.
2. **NOT RUN:** Original FM/IBK program names, exact bank metadata and SF2 `phdr` names
   display, with non-ASCII strings handled safely.
3. **NOT RUN:** Browser search/selection/PREV/NEXT maps to the actual processor
   program and produces distinct audible PCM where appropriate.
4. **NOT RUN:** SF2 bank/program selection persists and reopens with identical sound.
5. **NOT RUN:** VST3 GUI attach, close/reopen, zoom, automation and controller/processor
   synchronization in an automated host. Studio One is a separate final smoke test.

This spec intentionally makes no code changes to the current P14 development panel.
The owner requested agreement on function and content before final visual/GUI design.
