# START HERE — 125A AWE Synthesizer

**Stand: 2026-11-05. Entwicklungs-/Prüfstand, keine GUI- oder Releasefreigabe.**

## Verbindlicher aktueller Projektstand

- Repository: `challanger2000/125A-AWE-Synthesizer`.
- **Einziger aktiver Korrektur-Branch:** `fix/p122-bank-dirty-audit`. `main` ist **nicht** der aktuelle Entwicklungs-/Release-Stand; nicht ungeprüft übernehmen.
- **Aktuell Windows-getesteter P126-C++-Commit:** [`713dcc8cf69a4a644809a5d9b305a7900aca73c0`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/713dcc8cf69a4a644809a5d9b305a7900aca73c0).
- [**Windows Actions #42086496250: SUCCESS**](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42086496250) — realer Windows-x64-VST3-Build, native/VST3-Regressionstests, Metadaten, EditorHost und Testpaketierung. **Das ist kein unabhängiges Codex-GO.**
- Actions-Artefakte: `125A-P122-Windows-x64-VST3` (technischer Testbuild) und `125A-P122-EditorHost-GUI-Smoke`; kein freigegebenes Gumroad-/Releasepaket.
- **Neuester unabhängiger Codex-Status:** **P125 `805a2ef1` GUI-NO-GO / RELEASE-NO-GO.** Dessen schwere Fails sind [hier dokumentiert](docs/P126-BANK-ORDER-CORRECTION.md). **Ein unabhängiger P126-Nachaudit ist NOT RUN.**
- **READ-ONLY-Prüfauftrag:** [P126-Korrektur, Regressionen und vollständige Nachauditvorgaben](docs/P126-BANK-ORDER-CORRECTION.md).

## Chronologie der unabhängigen Befunde — NICHT mit grünen CI-Runs verwechseln

1. **P123**: Frühere korrigierte 30.000-Processor-State-Roundtrips, 500/500 Saves mit klingender Einzelstimme, Pan-Rate und Browser-Retry unabhängig PASS. Ein späterer Browser-Bankbefehl konnte einen älteren Recall nicht sicher überholen; `setProcessing` war `kNotImplemented` (beide HOCH).
2. **P124 `2f0c4d2`**: Processing-Handshake unabhängig **PASS**. Wieder **FAIL HOCH** bei bereits begonnenem Audioblock, dann Recall Bank 0, danach Bank 5 per Host-/MIDI-Bankqueue; Folgeblock setzte Bank 5 auf 0. `getTailSamples()==0` trotz ~0,9 s hörbarer Release-Tail.
3. **P125 `805a2ef1`**: Der zuvor scheiternde Audioblock/Recall/Bank5-Fall unabhängig **PASS**, die **umgekehrte zeitliche Richtung** jedoch **FAIL**. Weitere **HOHE Fails**: Browserauftrag geht verloren, MIDI-Kanaltrennung verletzt, neuerer Recall kann überschrieben werden. `kInfiniteTail` **PASS**, jedoch Chorus-Nachklang/Leerlauf weiter problematisch. Hohe CPU-Last; Wiederholung nur **498/500** erfolgreiche Saves. Daher **unabhängiges GUI-NO-GO / RELEASE-NO-GO** trotz grüner Windows-Tests.
4. **P126 `713dcc8c`**: Neuer eigenständiger `BankOrder` mit **drei gestempelten Quellen** (Recall bei Start, Browser-Notify, gewöhnlicher Host-Bankparameter), ohne alte unbedingte Browser-Snapshot-Quittierung. MIDI CC0/CC32 bleiben kanalbezogen mit eigener Zeitordnung; spätere Bankparameter werden bei Control-Gate-Kollision nicht vergessen. **Beide** Recall-Zeitfolgen und CC0-vs.-Browser im realen Windows-VST3-Test ergänzt. **Windows-CI SUCCESS; unabhängiges P126-GO NOT RUN.** Keine Änderungen an Sample-DSP, Chorus, RAM-Limit, ROM-Pflicht oder Stateformat.

## Noch offene Gates — GUI NO-GO / Release NO-GO

- **GUI-NO-GO:** Unabhängiger Codex-Nachaudit des **exakten P126-Codecommits** muss sämtliche ursprünglichen P125-FAIL-Szenarien wiederholen: *beide* zeitlichen Richtungen, normalen `PresetBrowserView::Select`-Parameterweg, explizite Re-Select-Nachricht, MIDI CC0/CC32 auf mehreren Kanälen, neuere vs. ältere Recalls, tatsächlich erklingende Bank, persistierte V10-Snapshots vor/nach Folgeblock, Browserfehler→Wiederverbindung, Host-Konformität und Negativmutationen. Nur eine erfolgreich klingende Demo genügt nicht. Fehlende Originalhardware-Klangparität allein ist nicht das GUI-Gate.
- **Release-NO-GO:** Zusätzlich CPU-/Deadlineprofil bei 16/30 Stimmen, dichtem Pitch und während Recall; Save-Verfügbarkeit, insbesondere P125 **498/500**; tatsächlicher Chorus-/Reverb-Nachlauf und `kInfiniteTail`-Host-/Idle-Kosten; echte Windows-Ziel-DAW/ASIO-Save/Close/Reopen, Original-ROM/SYNTHGM.SBK und autorisierte SF2-Audio-/Automations-Abnahme. Keine Erklärungen ohne Messung.
- Strict VST3 `setProcessing(true/false)` bislang unabhängig PASS; nicht ohne Nachweis als weiterhin defekt aufführen.
- **Keine Release- oder Gumroad-Pakete** bis eigener Release-Freigabe.

## Nach Classic — ausdrücklich zurückgestellte Ideen

- [Extended AWE Sampler / Sound-Blaster-Hybridsynth](docs/FUTURE-EXTENDED-AWE-SAMPLER.md): ROM + WAV-Layer, eigener Instrumenteneditor, später optional OPL3 und Creative-CQM-Vergleichsprojekte ADLplug-Next/OPL3GM. 1-GiB-Sampleverwaltung nur **Forschungsziel**, keine aktuell verfügbare EMU8000-Hardwareadressierung.
- **Nicht jetzt beginnen.** Zuerst unabhängiger P126-Audit, schwere Classic-Befunde, historische EMU8000-Effektvalidierung, GUI- und separate Release-Abnahme. Classic-Originalmodus weiterhin ROM-Pflicht und 28 MiB. Keine eigenmächtige Erweiterungsentwicklung.

## Entwicklung und Repository-Pflege

- Keine neuen P-Branches für kleine Korrekturen. Nacharbeiten ausschließlich im vorhandenen Branch. Frühere historische Stände als Tags `archive/pre-p122-cleanup/*` vorhanden.
- Öffentliche CI nutzt ausschließlich synthetische Test-Assets; Creative-ROMs/SBK und proprietäre SF2s niemals hochladen oder mitliefern.
- Historische PRs nicht ungeprüft schließen, Quellbranches nicht voreilig löschen.
- [Engineering-Guardrails](https://github.com/challanger2000/125A-Engineering/blob/main/ENGINEERING-GUARDRAILS.md) gelten für unabhängige Regressionen, negative Orakel und das Trennen von CI-Erfolg und tatsächlicher Freigabe.

Dieses Dokument hat Vorrang gegenüber älteren P13-/P124-/P125-Einleitungen.
