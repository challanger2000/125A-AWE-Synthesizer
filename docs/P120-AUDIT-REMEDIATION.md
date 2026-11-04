# P120 – P119 Nachaudit, gezielte Korrekturen und Freigabegrenzen

**Repository:** `challanger2000/125A-AWE-Synthesizer`  
**Branch:** `fix/p120-audit-remediation`  
**Basis:** P119 `fe7a4129afde21db399cfa661b37835108ee5a8f`  
**Ziel:** Nachweisbare Behebung der zehn P119-Auditbefunde mit regressionsfähigen Tests; keine Änderungen an authentischer EMU8000-Ausgangssättigung.

| P119 Befund | P120-Codeänderung | Prüfgate |
|---|---|---|
| 01 – ungebundene Engine-Retention | `RealtimeEngineExchange` verwendet Leser-Generationen und einen **Nicht-Audiothread-Collector**. Maximal vier zurückgehaltene Engines; nur der Kontrollthread wartet bei voller Queue. | `125A_p120_engine_retirement`: 1.000 überlappende Veröffentlichungen, `Collect()` nicht manuell aufrufen, alle alten Engines zeitnah und abseits Audio freigeben |
| 02 – keine kanalbezogenen Program Changes | VST3-`kIsProgramChange`-Parameter IDs 3000–3015 mit eigenen Unit-/ProgramList-Zuordnungen, `getUnitByBus`, 16 programmspezifische Audiozustände; globaler GUI-Program-ID 1000 bleibt bestehen | SDK-Hostparameter prüfen, 16 unterschiedliche Kanäle, GM Multi-Instrument PCM und Recall |
| 03 – alter CC0 schlägt neuen Browserbank-Recall | Neue Browser-/Recallbank invalidiert ältere CC0/32-Replay-Overrides; spätere MIDI-CC0-Befehle dürfen erneut gewinnen | `125A_p120_midi_automation`, echter ROM-/SF2-Wechsel samt Restore |
| 04 – Fade endet bei 62,5 % | Hostkurve steuert Master direkt, die 64-Sample-Entzipperung bleibt für manuelle Sprünge separat | `125A_p116_master_volume` misst **jeden** Samplewert gegen lineares Ideal und exakten 0-Endpunkt |
| 05 – Pitchbend punktdichteabhängig | Auch Pitchbend-Parameter nutzen `Curve`; während eines solchen Bends erzeugt `process()` samplegenaue Registerupdates. | `125A_p120_midi_automation` sparse/dense, originalromgestützter Audio- und CPU-Test weiterhin erforderlich |
| 06 – RPN zur gleichen Zeit falsch geordnet | Stabile Originalqueue-Ordinals plus deterministische Prioritäten CC101→CC100→CC6 am gleichen Sample | `125A_p120_midi_automation`, tatsächliche mehrere MIDI-Queue-Inputs erneut prüfen |
| 07 – alte Dirty-Vormerkung nach Recall | `setComponentState` löscht alte Dirty-Vormerkung, inkrementiert Zustellgeneration | nachgelagerte Controller-Hoststatusprüfung |
| 08 – endlose setDirty-Retry | Fehlt das optionale `IComponentHandler2`, beendet der Dispatcher den nutzlosen Retry statt mit 250-ms-Timer zu drehen | Hosthandler ohne Handler2, dauerhafte Ablehnung separat |
| 09 – UB bei 16-bit Register-Shift | Shift explizit als `uint32_t` statt signed-`int`. Oberes/unteres 16-Bit-Registermuster bleibt erhalten. | UBSan und Bitmustervergleich mit P119 |
| 10 – reentranter Controller-UAF | Dispatcher hält Controllerref durch Host-Callback und Win32-Timer-Bookkeeping; `DeliverHostSignals` hält eigenen Ref bis Rückkehr. | `125A_p120_ui_reentrancy`; tatsächliches Windows-EditorHost-Schließen mit ausstehender ACK/restart weiterhin nötig |

## Zustandsformat

Der bisherige globale Programmwert und alle bisherigen Parameter-IDs bleiben stabil. `AssetState` schreibt nun **Version 10** mit 16 zusätzlichen Programmen und einer expliziten Override-Maske. Alle alten Versionen **V1–V9 bleiben lesbar** und migrieren den globalen Programmwert auf sämtliche Kanäle. Projekt-Recall sowie `setComponentState` wurden mit den neuen Feldern erweitert.

## Ausstehende Gates

1. Erfolgreicher kompletter P120-Windows-2022-Build, CTests, Steinberg-VST3-Validator, dreifacher echter EditorHost-GUI-Lauf. Es werden ausschließlich Ergebnisse desselben P120-Commits anerkannt.
2. SDK-gestützte ProgramList-/Unit-/16-Kanal-Hosttests, nicht nur Header-Assertions.
3. Echtzeit-/Performanceprüfung bei dichter Pitchbend-Automation; Einzel-Frame-`RenderBlock` ist korrektheitsorientiert, kann aber unter Last teurer sein.
4. Echte Original-ROM-/`SYNTHGM.SBK`-Tests in Studio One mit aktivem Projekt-Recall, MIDI Program Change auf mindestens zwei unterschiedlichen Kanälen und laufenden ROM-/SF2-Wechseln.
5. Reentranter Shutdown mit echter Controllerinstanz, Windows-Sanitizer/Crashdump. Ein synthetischer Dispatcher-Test allein beweist die ursprüngliche sporadische EditorHost-Absturzursache **nicht**.
6. Unabhängiger **read-only Codex-P120-Nachaudit** vor jeder Release-/GUI-Freigabe.

**Freigabeentscheidung bis zu diesen Gates: NO-GO für Release und Gold-Faceplate.**

## Architektur- und Testgrenzen

- `RealtimeEngineExchange` setzt den dokumentierten Vertrag **eines serialisierten Prozess-Audiolesers pro Instanz** voraus. Parallele `process()`-Callbacks auf derselben Instanz sind nicht freigegeben.
- Der Collector darf ausschließlich auf einem Nicht-Audiothread große ROM-/SF2-Ressourcen vernichten. Er benötigt einen Wartungs-Thread pro Instanz, sobald tatsächlich ein Enginewechsel erfolgt.
- Bei voller Retired-Queue kann ausschließlich eine nicht-echtzeitfähige `Publish`-Operation auf eine sichere Freigabe warten.
- Das Schreiben einzelner numerischer RT-Atomics ist kein transaktionales Snapshotprotokoll bei gleichzeitigem `getState()`; Host-Konformität und mögliche Mehrfeld-Interleavings bleiben gesondert zu testen.
- Es werden keine proprietären Wave-ROMs oder Creative-Bänke ins Repository/CI-Paket aufgenommen.
