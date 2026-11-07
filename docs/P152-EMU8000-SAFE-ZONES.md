# P152 — Fixed PCB faceplate exclusions for the 125A AWE Synthesizer

**Reference:** functioning Windows VSTGUI at **1000 x 640 px**. Gold controls and the transparent pixel-based amber LCD are real VSTGUI controls; the PCB image has NOT been generated or installed.

## Reserved EMU8000 hardware area (must contain NO controls)

- Top-right IC bay: **(788,16)–(984,163)**, width 196, height 147.
- It is a graphics-only zone for a visually significant EMU8000 QFP-style IC, pins and physically plausible adjoining capacitors/traces, leaving a margin around raised parts.
- Approved gold `125A` branding remains at top left, and the amber LCD remains centered.
- If a 1:1 scale IC does not fit, **do not overlap** the live controls or move this area's bounds to accommodate it; adapt the artwork.

## Fixed header and navigation

- Header brand: (16,16)–(252,163), gold 125A identity.
- Amber LCD: (264,16)–(776,163). Dynamic top text: (310,52)–(534,71). Dynamic filename: (546,52)–(737,71). Dynamic program: (310,73)–(737,104). Dynamic hardware info: (310,107)–(737,126).
- Bank caption (23,184)–(65,214).
- Bank dropdown (67,179)–(193,218).
- Previous (202,179)–(242,218); Program dropdown (250,179)–(537,218); Next (545,179)–(587,218).
- SYNTH (597,179)–(690,218); BROWSER (698,179)–(797,218).
- ROM LOAD (808,177)–(885,218); SF2 LOAD (893,177)–(968,218).
- Bottom information line: (28,607)–(968,629).

## Fixed SYNTH control groups

- Reverb group: (16,234)–(190,409). Send knob (74,278)–(132,336); effect-type menu (32,382)–(174,405).
- Chorus group: (200,234)–(374,409). Send knob (258,278)–(316,336); menu (216,382)–(358,405).
- AMP ADSR group: (384,234)–(774,409), knob lefts x=408/502/596/690, y=278; every knob 58px and live caption/value below.
- Master group: (784,234)–(984,590), large knob (817,298)–(951,432), value (810,446)–(960,483), MOD RESET (808,535)–(960,571).
- FILTER ADSR group: (16,419)–(518,590), knob lefts x=48/169/290/411, y=464; every knob 58px.
- FILTER tone group: (528,419)–(774,590), knob lefts x=563/687, y=464, for cutoff and resonance.
- BROWSER page: visible only when selected; bank selector, search and list keep their P151 geometry.

## Binding constraints for final faceplate

1. Preserve the **original chosen golden 125A lettering** (never replace with a red logo).
2. All control rectangles, including label and value overlays, are keepouts for any raised PCB part. Add at least 8px decoration clearance whenever practicable.
3. Populate unused margins and the dedicated IC bay with gold traces, resistors, capacitors, smaller surface-mount ICs and ISA edge connector contacts.
4. Never draw preset names, ROM/SF2 filenames, status text, knobs, buttons or menus permanently into the background bitmap.
5. The P151 LCD, P149 knob strips and P150 button atlas remain independent, functional graphics.
6. Compare a fresh real Windows EditorHost screenshot after composing the eventual faceplate.
