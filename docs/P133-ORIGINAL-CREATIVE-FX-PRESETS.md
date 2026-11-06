# P133 – Originale Creative-Reverb- und Chorus-Auswahl, Windows VST3

**Datum:** 2026-11-06  
**Implementierung:** isolierter Branch `feature/awe-fx-preset-selection-v11-20261106`  
**PR:** [#72](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/72) (DRAFT, nicht gemergt)  
**Basis:** produktiver Entwicklungsbranch `fix/p122-bank-dirty-audit`, Start `c7d803c1`.

## Funktionsumfang

Zwei COptionMenu-Dropdowns auf der 1200×780 Hardware-GUI:

- **REVERB TYPE:** Room 1, Room 2, Room 3, Hall 1, Hall 2, Plate, Delay, Panning Delay.
- **CHORUS TYPE:** Chorus 1, Chorus 2, Chorus 3, Chorus 4, Feedback, Flanger, Short Delay, Short Delay + Feedback.

Die vorhandenen 12 SoundFont-Overlay-Regler, Masterlautstärke, SF2-Browser, Bank/Program-Auswahl und ROM-Ladefunktionen bleiben erhalten. RESET wurde nach unten versetzt; GUI-Smoke muss die neue physische Schaltfläche anklicken. Die Filter-/Master-Faceplate-Bereiche sind neu aufgeteilt, damit die beiden Menübezeichnungen nicht über den Trennlinien liegen.

**VST3 Host-Parameter:** `1200=Reverb Type`, `1201=Chorus Type`, je acht diskrete Schritte. Beide Controls sind GUI-seitig mit der maßgeblichen Host-Parametervalue synchronisiert, inklusive DAW-Automation.

**Effektengine:** Die acht **vorhandenen Original-Creative-Registerdatensätze** aus `Emu8000Effects.h` werden auf den tatsächlichen ROM-gestützten 86Box-EMU8000-Chip geschrieben, nicht allein auf die ungenutzten C++-Legacy-Reverb/Chorus-Klassen:

- Reverb: 28 Koeffizienten über INIT1–INIT4.
- Chorus: Feedback/Delay/LFO-Depth über INIT3/INIT4 und HWCF4–HWCF7. HWCF4=0 für Chorus 1–4, Feedback, Flanger; rechte Verzögerung für beide Short-Delay-Presets bleibt explizit.
- Keine neue Audio-Thread-Allokation, kein zusätzlicher Mutex, kein Wechsel zu einem generischen DAW-Reverb.
- Die mathematisch separate Chorus-Signed-Feedback-Draft-Reparatur [#67](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/67) wird **nicht** eingeschleust.

**Projektzustand:** `AssetState` V11 ergänzt zwei `uint32` Felder **am Ende** der V10-Daten. Original V1–V10 Binärlayouts bleiben unverändert lesbar. Default: Hall 2 (`4`), Chorus 3 (`2`). Ungültige Indizes >7 und abgeschnittene Daten werden ohne Teil-Commit verworfen.

**Echtzeit und Konkurrenz:** Stamped FX intents ermöglichen Save/Recall auch, wenn die RT-State-Writer-Gate wegen eines Hostprojektrecalls gerade nicht verfügbar ist. Bei neuen ROM/SF2-Engines werden beide gespeicherten Presets angewendet; neue Host-Automation muss einen veralteten Recall überholen. Effektauswahländerungen dürfen die Program- und Held-Note-Logik nicht verändern.

## Prüfungen

- `125A_asset_state`: V11 Vollroundtrip aller 64 FX-Kombinationen, negative/trunkierte Eingaben, V1–V10 Migration.
- `125A_p133_fx_register_modes`: originale 8+8 EMU8000 Registerdatensätze, alle 64 Kombinationen, Invalid-Indices.
- `125A_p133_fx_processor_modes`: echter SDK-extrahierter Produktionsprozessor, 64 Hostparametereinstellungen, Registerprüfung, Save bei verweigertem RT-Writer, spätere Anwendung, Projekt-Recall mit unabhängig konfigurierter 86Box PCM-Referenz.
- `p14_vstgui_contract.py`: statische Integration der beiden hostgebundenen Dropdowns; `p18_editorhost_smoke.py`: echter Win32 EditorHost, auch physischer RESET-Klick.
- Komplettworkflow: `.github/workflows/p133-fx-modes-full-windows.yml`, Windows 2022 / VS 2022 / x64 / C++23 / Steinberg SDK 3.8.1, **volle CTest-Suite**, vollständiger Steinberg VST3-Validator, drei GUI-Smokes. Erst nach vollständigem grünen Lauf wird ein **VST3 PREVIEW**-Artefakt hochgeladen, ausdrücklich **kein Gumroad-Release**.

**Vorläufiger P133-Gate-Stand:** Der Windows-Build auf `7720393f` bestand 43/43 CTests und 537/537 VST3-Validatorprüfungen. Der EditorHost scheiterte am alten RESET-Testkoordinatenwert, nicht an einem gecrashten Plugin; GUI-Testkoordinate und Faceplate sind daraufhin geändert worden. **Für den letzten Branch-Commit den aktuellen Windows-Actions-Lauf erneut nachsehen; ohne diesen Nachweis keine endgültige GUI-Abnahme.**

**Weiterhin offener Release-NO-GO:** Physische ASIO-/DAW-Deadlineprüfung (Codex P132 ist eine *andere* Untersuchung), Chorus-Hardwareparität C01, unabhängiger Gesamtaudit. Keine automatische Fusion von PR #72 oder Releasefreigabe.
