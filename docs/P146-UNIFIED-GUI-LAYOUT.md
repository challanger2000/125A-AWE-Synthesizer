# P146 — Functional VSTGUI layout first, hardware faceplate second

All existing AWE host parameters, ROM/SF2 loading and live information remain unchanged. The editor remains **1000 × 640 logical pixels** and now has exactly two UI pages:
- **SYNTH**: Master volume, Reverb Send + type, Chorus Send + type, AMP ADSR, FILTER ADSR, Cutoff, Resonance, modulation reset — **all permanently visible**.
- **BROWSER**: bank-filtered SF2 program search/table.

Bank / preset, ROM and SF2 loading, live status and the approved gold 125A branding stay visible regardless of page.

## Fixed rectangles for final PCB artwork
Coordinates are in VSTGUI logical pixels (x1,y1,x2,y2):
- Reverb Send (63,341,115,393), mode (32,444,149,470).
- Chorus Send (198,341,250,393), mode (167,444,284,470).
- AMP ADSR four 52px knobs: x=332,450,568,686; y=341.
- Master Volume **114px** (848,344,962,458) on right.
- FILTER ADSR four 52px knobs: x=54,181,308,435; y=495.
- Cutoff and Resonance 52px knobs: x=562,689; y=495.
- Modulation reset (832,516,975,551).
- Small knob labels occupy (x-20,y+61,x+82,y+81), values (x-20,y+82,x+82,y+101).
- Navigation: SYNTH (23,271,190,302), BROWSER (199,271,365,302).
- Persistent ROM/SF2, bank/preset, status and browser search positions are inherited unchanged from P145.

## Faceplate design constraints — only after functional acceptance
1. Reserve ALL above active rectangles, labels and value displays, with at least 8px extra room. Raised components and their shadows must never overlap them.
2. Preserve the specifically approved **gold 125A / AWE typography** (do NOT replace with alternate master logo).
3. Use the remaining areas for abundant plausible old ISA soundcard details: EMU8000 IC, smaller ICs, caps, resistors, gold traces, plated screws, bottom edge connectors.
4. The old P145 shared raster is an **interim** asset and is not redrawn in P146. Its old page-specific chip overlay was disabled as it conflicts with the new permanent controls.
5. Compare full real Windows EditorHost screenshot to the approved physical soundcard faceplate before approving assets.

No engine, MIDI, VST parameter ID, automation, file loading or state V11 changes in P146.
