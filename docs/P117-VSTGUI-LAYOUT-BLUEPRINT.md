# P117 – VSTGUI layout blueprint (before graphics)

**Design phase:** functional VSTGUI first; bitmap/metallic gold/PCB faceplate and gold 125A branding are the **second** phase. The working P116 is preserved unchanged on its branch.

## Fixed canvas and pixel grid

- Windows x64 VST3, VSTGUI, fixed logical client size **1200 × 780 px**, top-left origin (0,0).
- No unexplained overlays or popups. First-run browser opens by default.
- AWE64 Gold / EMU8000 vintage black+gold is the **visual reference**, not a claim to emulate the complete CT4390 analog board. All controls remain readable before graphics are introduced.
- **No changes to the audio engine or register emulation**. Retain P116's master, program, bank and 12 overlay parameters.

| Region | Bounding rectangle x1,y1–x2,y2 | Contains |
|---|---|---|
| Header | (12,8)–(1188,70) | Future new gold 125A brand, device title, EMU8000 |
| Live hardware display | (14,78)–(880,188) | Program name, selected bank, ROM/SF2/EMU8000 actual status |
| Asset actions | (891,78)–(1184,188) | Current SF2 filename, ROM LADEN, SF2 LADEN |
| Direct preset/navigation row | (14,198)–(781,267) | **Bank combo** (88–230), PREV (245–293), **direct program combo** (300–678), NEXT (690–739) |
| AMP envelope | (14,277)–(781,421) | Four knobs + 0–100% values |
| Filter envelope + tone | (14,429)–(781,588) | Six knobs + values |
| Master and effects | (14,596)–(781,746) | P116 master volume, Hall, Chorus, SF2 overlay RESET |
| Sound browser | (792,198)–(1185,746) | Browser on/off, bank FILTER, search, persistent scrollable preset list |
| Footer | (14,752)–(1185,778) | Actual audio/ROM/SF2 status, errors |

## The thirteen real knobs

| Control IDs | Function | Logic / placement |
|---|---|---|
| 1100–1103 | Amp Attack / Decay / Sustain Reduction / Release | AMP row, x=84/260/436/612, y=309 |
| 1104–1109 | Filter Attack / Decay / Sustain Reduction / Release / Cutoff Reduction / Resonance Boost | FILTER row, x=50/171/292/413/534/655, y=464 |
| 1003 | **Master Volume** | Separate, x=115,y=623; 0% silence, 100% unchanged original 125A output; smooth and automatable per P116 |
| 1110, 1111 | Reverb Send Boost / Chorus Send Boost | Output row, x=352/559,y=623 |
| GUI reset | Reset **only** 1100–1111 | Does **not** reset Master Volume, program, bank, ROM or SF2 |

The P116 overlay controls are 0% = original sound, whereas Master is 100% = original output. Keep these semantics visually separate. The master must not be used to mask P114/P115 hardware clipping.

## Direct preset behavior

- **PREV/NEXT** wraps *existing program entries in the currently selected bank*; no nonexistent gaps.
- **Program dropdown** lists real preset numbers AND full names from current `PresetCatalog`; clicking selects through the original VST3 host parameter IDs **1000 (program)** and **1002 (bank)**, using beginEdit/performEdit/endEdit.
- **Bank dropdown** lists *actual available banks* (including reserved ROM banks 16382/16383 when loaded). On bank switch preserve current program if valid there; otherwise select first available program.
- Search/filter of the large browser does not change PREV/NEXT or the direct dropdown's catalog; direct browser selection and host automation immediately synchronize name, menus and highlight.
- The direct program dropdown must have a visible placeholder when no ROM/SF2 catalog is available and must not emit fake host edits.
- Existing V9 state recall and host automation remain authoritative. No UI-only preset state.

## Status and safety

- 'ROM READY' / 'SF2 READY' / bank / program are derived from live controller/catalog/processor status, **not hardcoded green LEDs**.
- Avoid announcing active-voice counts without a real underlying sample counter; display capacity '32 VOICES' only.
- Real hardware-like LCD is a typography and frame treatment. It must still show text without any custom images or fonts.
- ROM/SF2 selectors, search, browser mouse and keyboard selection, loading/error status, VST3 parameter-only process, stereo/mono output, no-ROM silence, and state migration V1–V9 must continue working.
- High DPI scaling handled by VSTGUI/host; all rectangles in VSTGUI logical coordinates.

## Acceptance gates

1. CI builds full Win x64 Steinberg-SDK VST3 (real EditorHost smoke).
2. Updated structural contract checks exact 1200×780 view and all 13 knobs.
3. Unit tests verify sparse-bank PREV/NEXT and direct bank/program catalog selection.
4. All existing CTests pass, no exceptions/missing assets, and P116 default 100% master is retained.
5. A screenshot of the real, working first-stage panel is reviewed before **any** metallic gold faceplate or custom knob artwork is inserted.
6. Subsequent GUI skins change only drawing/resources, not parameter IDs/audio output.

**Art direction for the later skin**: black PCB, restrained gold traces, tasteful gold 125A logo like the approved preview (original logo not required), amber display, metallic knobs, decorative ISA edge connectors; avoid imitation of an actual Creative trademark or falsely claiming board-level CT4390 emulation.
