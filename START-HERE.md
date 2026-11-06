# START HERE — 125A AWE Synthesizer

**Stand: 2026-11-06. Entwicklungs-/Prüfstand, keine GUI- oder Releasefreigabe.**

## AKTUELL – P128 unabhängig behobene Konkurrenzfehler, P129 Effekt-Audit (6. November 2026)

- **Produktions-/Entwicklungsbranch** ist ausschließlich `fix/p122-bank-dirty-audit`, weiterhin **kein Release**. Über [PR #65](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/65), Merge-Commit `ac2cab282b2c1ed89dc9aee82feb4364c6e810c1`, wurden zwei **zuvor unabhängig reproduzierte** Fehler mitsamt Dauer-Regressionen integriert:
  1. **Master-/GUI-Automation unter RT-Writer-Gate** geht nicht mehr verloren, auch bei verzögertem Projekt-Recall; Test `125A_p128_persistent_controls`.
  2. **ProgramChange vor NoteOn im selben Audioblock** verwendet auch bei Writer-Gate-Kollision den bereits akzeptierten Sound; globale und kanalbezogene Programme mit PCM-Identität und V10-Override-Masken; Test `125A_p128_sample_accurate_program_pcm`.
- **[Produktions-Regression nach Merge #42170408839: SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42170408839): 40/40 CTests, 47/47 Steinberg VST3-Validator, 3/3 Windows-EditorHost-GUI-Smokes.** Die Ergebnisse sind echte Windows-Prüfungen, kein unabhängiger Gesamt- oder DAW-Releaseaudit. Siehe [Issue #64](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/64).
- **P129 Chorus:** die endlose negative Integer-Feedback-Restschleife in `emu8k_work_chorus()` wurde mit direkten Windows-Chiptests reproduziert. Ein mathematisch symmetrischer Quantisierungsfix ist vorbereitet: Original vs Kandidat in acht identischen PCM-Stimuli verglichen, Änderungen bei Feedback-Presets maximal 1–7 Roh-Integer-LSB, zwei Presets ohne Feedback bitidentisch. **[Draft PR #67](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/67)** enthält den neuen dauerhaften DSP-Regressionstest, bleibt **unmerged**, da die genaue Hardware-DSP-Rundung noch nicht unabhängig belegt ist. Siehe [Issue #66](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/66).
- **Echtzeit, jüngste P129-Nachprüfung:** Die frühen, weniger anspruchsvollen Windows-Szenarien ([2.000 Renderblöcke](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42166510626), [1.500 `process()`-Callbacks](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42167569125)) hatten keine Überläufe. **Die erweiterte Matrix mit 128/256/1.024-Sample-Puffern, 4 neuen MIDI-Noten pro Block und gleichzeitigem V10-Save/Recall hat dagegen 8 von 4.500 realen `process()`-Deadlineüberschreitungen** nachgewiesen, sowohl mit grobem Windows-Timer ([#42172652356](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42172652356)) als auch mit korrekt angeforderter 1-ms-Timerauflösung ([#42173714104](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42173714104)). Daneben stehen **gesonderte Windows-Scheduler-Verzögerungen**, die durch die bessere Timerauflösung abnahmen; sie sind nicht gleichzusetzen mit Plugin-Berechnungsüberläufen. Der Produkt-Processor wurde im eigenständigen Audit-Branch `audit/p129-smallbuffer-save-recall-20261106` getestet, keine Produktions-DSP-Änderung. **RT-Deadline-FAIL auf Windows-CI-Versuchsstand; Studio-One-/ASIO-Abnahme und Linux-Überläufe weiter OFFEN.** Vollständige Werte in [Issue #66](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/66).
- **Verbindliche Gates:** Hardware-nahe Chorusklangvalidierung, ASIO/DAW-Abnahme und umfassender unabhängiger Releaseaudit sind **OFFEN**. **GUI: NO-GO; RELEASE: NO-GO; Gumroad-Paket: NICHT ERSTELLEN.** Nicht einzelne erfolgreiche CTests als Freigabe umdeuten.

## P128 – lokale Nachprüfung und Korrekturen (6. November 2026)

- Entwicklungsbasis: `105f756f15253001ee1cd49a234c584ea60fca77` auf `fix/p122-bank-dirty-audit`.
- [Konkrete Reproduktionen, Korrekturen, Testgrenzen und offene Gates](docs/P128-NATIVE-REAUDIT-AND-CORRECTIONS.md): drei Programm-/Recall-Gate-Rennen, verlorene NoteOns beim Enginewechsel und ein Nullpointer-Absturz nach Engine-Entfernung wurden lokal nachgewiesen und mit Regressionen korrigiert. Eine exakt invalidierte Filterkoeffizienten-Ablage vermeidet identische teure Neuberechnungen; PCM-Vergleich gegen die ursprüngliche und eine ungecachte Engine bleibt bytegleich.
- **Neuer Windows-Lauf [#42163215752](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42163215752) auf `7cb23c26c4199091ed1430641c29def168c51757`: SUCCESS** — reale VST3, 38 CTests, Validator im Build und 3 EditorHost-Smokes. Native Linux-/SDK-Prüfungen: 31/31. **Chorus-Reste weiter FAIL (18/24 Tail-Fälle), Echtzeit-Deadlines weiter FAIL.** Die Entwicklerregressionen ersetzen keine vollständige unabhängige P128-/Ziel-DAW-Abnahme. GUI-NO-GO und RELEASE-NO-GO bleiben bestehen.

## P128 – unabhängige technische Prüfung im 125A Plugin Test Lab (6. November 2026)

- **Geprüfter AWE-Code/Binärbuild:** P128 `9080fe75e57dd11c8019898ff481ae11839fedc4`, Windows-Artefakt aus [Actions #42146715681](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42146715681).
- **Unabhängiges Test-Lab:** öffentliche Quellen aus `challanger2000/125A-Plugin-Test-Lab` auf **`70f9e40d081f98e3dde368daddbabd268d74047b`** gepinnt. Eigenständiger nativer Windows-x64-Build der vier Testhosts.
- **[Test-Lab-Integration #42150123608: SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42150123608)** mit technischem Evidenzartefakt `125A-AWE-P128-Test-Lab-Technical-Evidence`: echte VST3-Stressmatrix (6 Raten/Puffer-Kombinationen, 15.000 Callbacks und 3.000 Saves), frische Processor-Recalls, zwei Instanzen in einem Hostprozess, echte GUI-Lifecycle-Prüfung; technische Quickcheck-Entscheidung **TECHNICAL_PASS**, `release_approved=false`.
- **WICHTIGE GRENZE:** Ohne Original-ROM und produktspezifische synthetische SF2-/PCM-Orakel wurden **keine AWE-spezifischen Bank-/Programm-/Recall-Rennen**, keine musikalische Klangrichtigkeit, keine getrennten Presetklänge, keine echte DAW-Session und keine Hardwareparität nachgewiesen. Der unabhängige **P128-Nachaudit der P127-F01 bis F06 ist hierdurch NICHT ersetzt**. **GUI-NO-GO und RELEASE-NO-GO** bleiben.
- **Wiederholbarer technischer Workflow:** `.github/workflows/p128-test-lab-integration.yml`; verwendet vorerst die auf sieben Tage begrenzten Artefakte des gepinnten Windows-Builds. Für spätere Wiederholungen muss der Build-Artefaktbezug auf einen noch verfügbaren, exakt identifizierten Build aktualisiert oder der VST3 neu gebaut werden. Am Repository des Test Labs wurde nichts verändert.

## Verbindlicher aktueller Projektstand

- Repository: `challanger2000/125A-AWE-Synthesizer`.
- **Einziger aktiver Korrektur-Branch:** `fix/p122-bank-dirty-audit`. `main` ist **nicht** der aktuelle Entwicklungs-/Release-Stand; nicht ungeprüft übernehmen.
- **Aktuell Windows-getesteter P127-C++-/Testcommit:** [`9e9a8dd5a4d3299e0d7a708b0d5144e5886fdea5`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/9e9a8dd5a4d3299e0d7a708b0d5144e5886fdea5).
- [**Windows Actions #42101410960: SUCCESS**](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42101410960) — realer Windows-x64-VST3-Build, native/VST3-Regressionstests inkl. neuer Recall-/Programm-Fälle, Metadaten, EditorHost und technische Testpaketierung. **Kein unabhängiges P127-GO.**
- Actions-Artefakte: `125A-P122-Windows-x64-VST3` (technischer Testbuild) und `125A-P122-EditorHost-GUI-Smoke`; kein freigegebenes Gumroad-/Releasepaket.
- **Neuester unabhängiger Codex-Status:** **P126 `713dcc8c` Bank/Recall FAIL, GUI-NO-GO, RELEASE-NO-GO.** Alle früheren engen P125-Bankfälle wurden bestanden, aber F01–F03 zeigten neue schwere Recall-/Pending-/Save-Rennen; F07 vollständiges Browserpreset (5,9) wurde als (5,0) gespeichert. F04 Chorus-Rest, F05 499/500 Saves und F06 Deadline-Überschreitungen bestehen. **Unabhängiger P127-Nachaudit: NOT RUN.**
- **READ-ONLY-Prüfauftrag:** [P127-Korrekturen, P126-Fehlerreproduktionen und vollständige unabhängige Nachauditvorgaben](docs/P127-RECALL-SAVE-PRESET-CORRECTION.md).

## Chronologie der unabhängigen Befunde — NICHT mit grünen CI-Runs verwechseln

1. **P123**: Frühere korrigierte 30.000-Processor-State-Roundtrips, 500/500 Saves mit klingender Einzelstimme, Pan-Rate und Browser-Retry unabhängig PASS. Ein späterer Browser-Bankbefehl konnte einen älteren Recall nicht sicher überholen; `setProcessing` war `kNotImplemented` (beide HOCH).
2. **P124 `2f0c4d2`**: Processing-Handshake unabhängig **PASS**. Wieder **FAIL HOCH** bei bereits begonnenem Audioblock, dann Recall Bank 0, danach Bank 5 per Host-/MIDI-Bankqueue; Folgeblock setzte Bank 5 auf 0. `getTailSamples()==0` trotz ~0,9 s hörbarer Release-Tail.
3. **P125 `805a2ef1`**: Der zuvor scheiternde Audioblock/Recall/Bank5-Fall unabhängig **PASS**, die **umgekehrte zeitliche Richtung** jedoch **FAIL**. Weitere **HOHE Fails**: Browserauftrag geht verloren, MIDI-Kanaltrennung verletzt, neuerer Recall kann überschrieben werden. `kInfiniteTail` **PASS**, jedoch Chorus-Nachklang/Leerlauf weiter problematisch. Hohe CPU-Last; Wiederholung nur **498/500** erfolgreiche Saves. Daher **unabhängiges GUI-NO-GO / RELEASE-NO-GO** trotz grüner Windows-Tests.
4. **P126 `713dcc8c`**: Gemeinsame Bankereignisordnung und kanalbezogene MIDI-Bank-CCs. Windows-CI SUCCESS und unabhängige alte P125-Bankorakel PASS. **Aber unabhängiger Nachaudit FAIL:** ein älterer Recall überschreibt einen neueren, ein vor dem RT-Gate gelesener alter Bankauftrag produziert falsches PCM/Save, und eine akzeptierte Bank wird bei unmittelbarem Save vor dem Folgeblock verloren. Browserprogramm 9 wird durch altes Recallprogramm 0 überschrieben. **GUI-NO-GO, RELEASE-NO-GO.**
5. **P127 `9e9a8dd5`**: Monotoner Recall-Commit mit Rückweisung überholter Recalls, frische Bankauswahl erst *innerhalb* des RT-Schreibgates, speicherbarer Pending-Bankwert sowie nicht-RT-Save-Fallback bei erschöpften optimistischen Versuchen. Neue Programm-Intent-Reihenfolge soll Browserpreset (5,9) zusammenhalten. Zusätzliche native/echte Windows-VST3-Regressionen für Doppel-Recall und Bank/Programm nach pausiertem Recall. **Windows Actions #42101410960 SUCCESS; unabhängige P126-Originalreproduktionen auf P127 NOT RUN.**

## Noch offene Gates — GUI NO-GO / Release NO-GO

- **GUI-NO-GO:** Unabhängiger Codex-Nachaudit des **exakten P127-Codes `9e9a8dd5`** muss zuerst die **Originalreproduktionen P126-F01/F02/F03/F07** unverändert wiederholen, einschließlich überlappender/reentranter Recalls, alter Bankwahl vor RT-Gate, akzeptiertem Bankwechsel bei besetztem Writer-Gate mit **sofortigem Save vor dem nächsten Audioblock**, sowie voll klingendem Browserpreset (Bank 5/Programm 9 gegen Bank 5/Programm 0). Echte synthetische ROM/SF2-Klänge, 16 Kanäle, V10-Roundtrips, unterschiedliche Programmsamples und Negativmutanten erforderlich. Erfolgreicher Windows-Build ist kein GUI-GO.
- **Release-NO-GO:** Zusätzlich P126-F05 **zweimal 499/500** Saves unter Programmautomation+Recall; P127 enthält einen Control-seitigen Save-Fallback, dessen Lastwirksamkeit **noch nicht unabhängig bewiesen** ist. Audio-Deadlines bei 30 Stimmen/dichtem Pitch weiter FAIL; Chorus-Rest trotz `kInfiniteTail` (−1 PCM-LSB und je nach Preset mehr) bleibt offen. Original-ROM/SYNTHGM.SBK, autorisierte SF2-Audiovergleiche und echte Ziel-DAW/ASIO-Save/Close/Reopen/Offline-/Idle-Abnahme NOT RUN. Keine Erklärung ohne reale Messungen.
- Strict VST3 `setProcessing(true/false)` bislang unabhängig PASS; nicht ohne Nachweis als weiterhin defekt aufführen.
- **Keine Release- oder Gumroad-Pakete** bis eigener Release-Freigabe.

## Nach Classic — ausdrücklich zurückgestellte Ideen

- [Extended AWE Sampler / Sound-Blaster-Hybridsynth](docs/FUTURE-EXTENDED-AWE-SAMPLER.md): ROM + WAV-Layer, eigener Instrumenteneditor, später optional OPL3 und Creative-CQM-Vergleichsprojekte ADLplug-Next/OPL3GM. 1-GiB-Sampleverwaltung nur **Forschungsziel**, keine aktuell verfügbare EMU8000-Hardwareadressierung.
- **Nicht jetzt beginnen.** Zuerst unabhängiger P127-Audit und alle noch schweren Classic-Befunde, historische EMU8000-Effektvalidierung, GUI- und separate Release-Abnahme. Classic-Originalmodus weiterhin ROM-Pflicht und 28 MiB. Keine eigenmächtige Erweiterungsentwicklung.

## Entwicklung und Repository-Pflege

- Keine neuen P-Branches für kleine Korrekturen. Nacharbeiten ausschließlich im vorhandenen Branch. Frühere historische Stände als Tags `archive/pre-p122-cleanup/*` vorhanden.
- Öffentliche CI nutzt ausschließlich synthetische Test-Assets; Creative-ROMs/SBK und proprietäre SF2s niemals hochladen oder mitliefern.
- Historische PRs nicht ungeprüft schließen, Quellbranches nicht voreilig löschen.
- [Engineering-Guardrails](https://github.com/challanger2000/125A-Engineering/blob/main/ENGINEERING-GUARDRAILS.md) gelten für unabhängige Regressionen, negative Orakel und das Trennen von CI-Erfolg und tatsächlicher Freigabe.

Dieses Dokument hat Vorrang gegenüber älteren P13-/P124-/P125-/P126-Einleitungen.
