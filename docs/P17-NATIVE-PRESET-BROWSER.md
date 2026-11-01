# P17 — Native VSTGUI Preset Browser

Development browser; visual design/125A master logo to follow after actual UI acceptance.

## Controls (real, not mock)

| Widget | Input | VST3 parameter / effect |
| --- | --- | --- |
| HARDWARE | menu EMU8000/OPL3/CQM | existing ID 1001, 0/1/2 |
| Hardware description | auto | UI-only description changes on mode/recall |
| PREV / NEXT | button | existing ID 1000, navigates only actual programs in active bank |
| Current program | read-only display | real SF2 phdr / IBK name plus bank and program number |
| BROWSER | toggle | shows/hides search, bank filter, scrollable list (UI-only) |
| Bank filter | menu of real loaded banks or ALL | filters list, does not change sound without selected preset |
| Search | immediate text filter | case-insensitive query of original program name |
| Program table | mouse/keyboard selection | ID 1002 bank first, then ID 1000 program; audio is not loaded on UI thread |
| Host automation / reopen | idle UI sync | read IDs 1000, 1001 and 1002 from Steinberg controller |

## Guarantees

- No 128-row OS popup, full scrolling browser table instead.
- No invented General MIDI names; names come from phdr or historical IBK metadata.
- No new SF2/ROM file requirement and no audio-thread disk access.
- Missing SF2 clearly displays no loaded presets rather than fake names.
- Bank 128 is labelled as drumkits and selectable even on melodic channel 1.
- All 3 hardware descriptions are visible directly under the Hardware selector.
- Existing project V7 data and VST3 IDs 1000/1001/1002 are unchanged.
- Search and bank filter are view-only; choosing a row edits VST3 state.

## QA

- Native preset model assertions appended to P16 CTest: case-insensitive searches, sparse banks, drumkit and FM bank names, PREV/NEXT wrap, hardware help text.
- P14 VSTGUI static contract now *rejects* the old long Program popup and requires P17 native controls.
- Windows VST3/Validator/actual host verification required before claiming PASS.
- Real Studio One browser click/typing, scaling, project recall and final visual polish are separate acceptance gates.

**Scope boundary:** The display is a functional dark prototype and deliberately does not counterfeit the authoritative 125A vector logo. Final Sound-Blaster-style faceplate and branding come after functional acceptance.