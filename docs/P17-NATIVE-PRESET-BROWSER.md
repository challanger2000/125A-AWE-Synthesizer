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
## Verifizierter Entwicklungsstand — 2026-11-01

- Autoritativer getesteter Quellstand: `4789270dd6bb73c083ef1739322abccb9c07bc7d` (PR #12, Korrektur PR #13).
- Windows-VST3: [GitHub Actions #41268102138](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41268102138), **SUCCESS**.
- 15/15 CTests PASS, einschließlich Modelltests für SF2/IBK-Browser-Suche, Bankfilter und PREV/NEXT.
- Steinberg VST3 Validator: **47/47 PASS**, im selben Windows-Lauf.
- Nativer Engine-Safety-Lauf: [#41268102123](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41268102123), **13/13 PASS**.
- Artifact: `125A-AWE-Synthesizer-Windows-x64-DEV` (vollständiger `.vst3`-Ordner einschließlich Ressourcen).

**NICHT AUSGEFÜHRT / NOT RUN:** tatsächliches Öffnen, Darstellung, Scrollen, Anklicken und Tippen des Browsers in einem laufenden Windows-VST3-Host; Host-Parameter- und Projekt-Recall-End-to-End; Studio-One-Praxistest; endgültiges Sound-Blaster-Retro-GUI mit autorisiertem 125A-Masterlogo.

**P17-Backend und Windows-Build geprüft, GUI-Host-Abnahme noch offen. Kein FINAL/Gumroad-Paket.**