# P127 — Recall-Commit, Bank-Snapshot, Save-Verfügbarkeit, Browser-Preset (Korrekturkandidat)

**Stand: 2026-11-05. GUI-NO-GO / RELEASE-NO-GO. Kein Releasepaket.**

**Verbindlich geprüfter C++-/Testcommit:** [`9e9a8dd5a4d3299e0d7a708b0d5144e5886fdea5`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/9e9a8dd5a4d3299e0d7a708b0d5144e5886fdea5).

**Windows x64:** [GitHub Actions #42101410960 — SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42101410960). Reale VST3-DLL, vorhandene native/VST3-Regressionen samt neuer Hostfällen, Metadaten, EditorHost-GUI-Smokes und technische Testpaketierung erfolgreich. **Kein unabhängiges P127-Codex-GO.**

## Anlass: unabhängiger P126-Nachaudit war FAIL

Der vom Projektinhaber übermittelte vollständige P126-Audit des **Codecommits `713dcc8cf69a4a644809a5d9b305a7900aca73c0`** meldet:

- **P126-F01 HOCH:** Recall A beginnt, pausiert beim ersten V10-Read. Der neuere Recall B (Bank 5) beendet sich, dann publiziert A trotzdem Bank 0 und überschreibt Bank, Klang und spätere Projekt-Saves. Grund: `BankOrder::CommitRecall` machte einen **unbedingten Store**, die Engine-Assetgeneration wird erst nach dem Streamread gesampelt.
- **P126-F02 HOCH:** Audio liest Browserbank 5 vor dem RT-Writer-Gate. Ein neuerer Recall 0 beendet sich. Audio erwirbt danach erst das Gate, **wendet den alten Bank-5-Snapshot an** und startet in diesem Block eine Note mit falschem PCM. Erst Folgeblock heilt die Bank, nicht aber den inzwischen gespeicherten falschen V10-State.
- **P126-F03 HOCH:** Bankparameter 5 wird nach Recallbeginn auf dem Audiopfad akzeptiert und als Pending publiziert, trifft aber das besetzte Control-Gate. Der Callback kehrt erfolgreich zurück. Ein **sofortiger** erfolgreicher Host-Save vor dem nächsten Audioblock enthält trotzdem Bank 0. Bei Projektende geht die anerkannte Änderung verloren.
- **P126-F07 MITTEL:** Beim normalen Browserpfad `PresetBrowserView::Select(5,9)` nach Beginn eines alten Recalls gewinnt zwar die neue **Bank 5**, aber der alte **Programmwert 0** überschreibt Programm 9. Browser/Controller zeigen (5,9), Engine/Save (5,0). Die verwendete synthetische Bank-Fixture enthielt innerhalb einer Bank gleiche Wellenformen für die Programme; eine korrekte Programm-PCM-Unterscheidung war dadurch **nicht** belegt.
- **P126-F05/F06 RELEASE-NO-GO:** Unter dichter Programmautomation plus Recall **zweimal 499/500** Saves. Bei 30 Stimmen bzw. 16 Stimmen+128 Pitchpunkten wiederholte **Deadline-Überschreitungen** oberhalb des 23,22-ms-Budgets bei 44,1 kHz/1024 Frames. P126-F04 Chorus-Feedback-Rest bleibt bestehen, insbesondere **−1 PCM-LSB nach 60 s**, abhängig von Hardware-Chorus-Preset auch mehr. `kInfiniteTail` selbst ist weiterhin korrekt.
- **P126 bestanden:** enge P125-Bankmatrizen und Kanaltrennung, 120.000 definiert kohärente State-Roundtrips, 27 native CTests, ASan/UBSan-Teilmatrix und sechs gezielte Negativmutationen. **Kein Schluss auf Gesamtfehlerfreiheit.**
- Im unabhängigen Bericht sind Windows-DLL-/GUI-, Originalhardware-/Original-ROM- und Ziel-DAW-Prüfungen **NOT RUN**; der separate vorherige Windows-Workflow von P126 war SUCCESS.

**Quellgrenze:** Der vollständige P126-Audit wurde vom Projektinhaber als Textdatei zur Verfügung gestellt; die fremden temporären Pfade `/tmp/P126-Nachaudit-713dcc8c.md` und `/tmp/P126-Nachaudit-Artefakte-713dcc8c.tar.gz` sind keine dauerhaft ins Repo eingebundenen Artefakte. Befunde hier sind aus dem Audit übernommen und nicht als neue eigene Reproduktionen behauptet.

## Implementierte P127-Korrekturen

1. **Monotoner Recall-Commit** in `BankOrder.h`: `CommitRecall(sequence, bank)` verwendet ein sequenzmonotones Compare/Exchange und gibt bei einem bereits jüngeren Recall **false** zurück. `Factory.cpp::setState` beendet einen so überholten alten Recall mit `kResultFalse`, **ohne** dessen alte Projektfelder, Engine oder Bank zu publizieren. VST3-Hostverhalten bei diesem abgewiesenen überholten Recall muss unabhängig überprüft werden.
2. **Bankentscheidung nach erfolgreichem Writer-Gate erneut lesen** in `Factory.cpp::ApplyPendingGlobalBank`. Der vor Gateerwerb gelesene Bankwert ist nur noch eine Pending-Vorprüfung. Innerhalb des Gates werden Recall-Invalidierung und **aktuellste Bankauswahl** erneut bestimmt; der alte 5er-Snapshot darf einen neueren Recall 0 nicht überholen.
3. **Sofort speicherbare akzeptierte Bankänderung:** `getState` liest die `BankOrder`-Entscheidung gemeinsam mit dem versionierten Echtzeit-Snapshot; es verwendet nicht ausschließlich den möglicherweise veralteten `rtBank_`-Wert. Bei schnellem konkurrierendem Schreiber und erschöpften 4096 Optimistikversuchen erstellt die **nicht-realtime** Save-Seite einen kohärenten Snapshot mittels `engineMutex_` und `RealtimeStateVersion::Writer(Control)` statt willkürlich `kResultFalse` zurückzugeben. Der Audiothread erhält keine neuen Locks, Warteschleifen oder Allokationen. **Diese Fallback-Verfügbarkeit ist noch nicht unabhängig unter P126-Last gemessen.**
4. **Bank/Programm-Presetkonsistenz:** Erfolgreiche globale VST3-Programmänderungen erhalten im Audiowriter dieselbe gemeinsame Intent-Ereignisordnung wie Banken/Recalls. Bei einem spät abschließenden älteren Recall wird eine neuere globale Programmwahl samt `channelProgramMask=0` und 16 übereinstimmenden Programmen in State und vorbereitete Engine übernommen. Damit soll `Select(5,9)` nicht heimlich `(5,0)` erzeugen. **Kein vollständiger atomarer VST3-Host-Bank/Programm-Gestenvertrag behauptet**; der unabhängige Audit muss auch per-channel Programme und Host-Queue-Rennen challengen.
5. **Zusätzliche Windows-/native Regressionen:** echter aus der VST3-DLL erzeugter Processor mit zwei überlappenden `setState()`-Aufrufen (alter Recall im echten Stream-Read pausiert, neuer Bank5/Programm9 erfolgreich, alter muss abgewiesen werden); echter Host-Parameterflush Bank5/Programm9 während eines alten Bank0/Programm0-Recalls, Save und Folgeblock müssen vollständiges Preset (5,9) erhalten; native `BankOrder`-Checks für alte/neue Recallpublikation und veraltete Gate-Vorabentscheidungen.

## Unabhängiger P127-Nachaudit — READ ONLY, exakter Code 9e9a8dd5

**Weder Dateien, Commits, Branches noch Konfigurationen ändern.** Testquellen, synthetische Assets, Negativmutanten, Builds und Berichte außerhalb des Repositorys. Ursprüngliche P126-F01/F02/F03/F07-Reproduktionen **unverändert zuerst** ausführen und ergänzend genau kontrollierte Abbruch-/Negativfälle einbauen.

**A. F01 (zwei Recalls, auch reentrant):**
- R_alt=Bank0/Programm0 startet, blockiert im ersten V10-Read; R_neu=Bank5/Programm9 endet vollständig; R_alt wird freigegeben.
- State, Engine, *tatsächliche* PCM nach Rückkehr, Folgeblock und Save in frischer Instanz müssen alle bei (5,9) bleiben. Sowohl zwei Control-Threads als auch verschachtelter Recall im `IBStream::read`-Callback. Ablehnung des alten Recalls (nicht stiller Erfolg mit falschem Zustand) als eigenes Ergebnis protokollieren.
- Reverse-Positivkontrolle: neuere Recallstart-Reihenfolge gewinnt auch bei langsamer ROM-/SF2-Vorbereitung.

**B. F02 (Bank-Snapshot VOR RT-Gate):**
- Browserbank 5 akzeptiert; Audio wird unmittelbar **nach dem ersten `BankOrder::Latest()`**, aber VOR `RealtimeStateVersion::Writer(Audio)` pausiert. Neuer Recall 0 beendet sich. Danach Audio freigeben und eine echte Note in demselben Block rendern.
- **Erwartet:** Bank0-PCM und Bank0-State direkt nach diesem Block, nicht 0→5→0, keine falsche V10-Datei im Zwischenzustand.
- Programmwechsel, CC0/CC32 und neue Notify-Nachricht im selben zeitlichen Umfeld als Gegenproben.

**C. F03 (Save VOR dem nächsten Audio-Callback):**
- Recall-Commit hält Control-Writer-Gate und pausiert nach seinem Bank-`Latest`-Snapshot. Parallel akzeptiert `process` `kBankID=5` und kehrt erfolgreich zurück, ohne die Engine sofort ändern zu können. Recall beendet sich.
- **Ohne** zusätzlichen Audioblock `getState` ausführen und gespeicherte Bank sofort in einer frischen Processor-Instanz wiederherstellen. **Erwartet 5**, nicht 0. Gegenprobe: neuere Recalls oder Browseraufträge müssen legitim gewinnen; Snapshot darf nicht andere Programmfelder mischen.
- Vergleich mit bewusstem altem `rtBank_` als negative Mutation: Das Orakel muss 0 statt 5 erkennen.

**D. F07 (vollständige Browser-Presetwahl):**
- Echter `PresetBrowserView::Select(5,9)` mit echten Host-Edits und Processor-Queues, während ein älterer Recall (0,0) pausiert. Browser, Controller, Processor, gespeicherter V10-State und frischer Processor müssen sämtlich **Bank 5 / Programm 9** liefern.
- **Synthetische Fixtures mit sowohl bank- ALS AUCH programmspezifisch hörbar verschiedenen Wellenformen verwenden**: (5,0), (5,9), (0,0), (0,9) müssen unabhängig unterscheidbar sein. Keine reine Bankklangprobe als vollständigen Preset-PASS ausgeben.
- Programmänderung gegen neueren Recall und 16 individuelle MIDI-Kanalprogramme/Override-Maske, Stichproben um Writer-Gate-Kollisionen.

**E. Save-Verfügbarkeit und Last:**
- 30.000/30.000/30.000/30.000 kohärente RT-/Control-State-Roundtrips, dabei den neuen Save-Fallback und pending Bank/Programm kombinieren. 
- P126-Originalbelastung mit 500 echten `getState` je Lauf: 1/16/30 Stimmen, 16 Stimmen + 128 Pitchpunkte, 1024 globale Programmpunkte mit/ohne Recall, gezielte Wiederholungen. Alle vollständigen Streams dekodieren; **499/500 ist FAIL**, auch wenn die übrigen gültig sind.
- Audio-Thread weiterhin ohne Blockieren/Allokationen. Fallback-Control-Wait und 44,1 kHz/1024-Callbackdauer mit CPU-/Wallzeit getrennt messen; Deadline-Überschreitungen nicht als behoben melden.

**F. Separat weiterhin RELEASE-NO-GO:**
- Chorus-Rest/Integer-Feedback-Fixpunkte einschließlich acht Presets, 44,1/48/96 kHz und (wo praktisch) längere Tailfenster; Zielhost mit `kInfiniteTail` für Idle/Offline **NOT RUN**, sofern nicht wirklich ausgeführt.
- `setProcessing`-Lifecycle, Voice-/State-Retirement, Panning, Pitchbend/RPN, Bank-CC-Channel-Trennung und Host-Fehler-Retry dürfen keine Regression zeigen.
- Keine eigenmächtige DSP-Änderung, kein Pro-Forma-Release und kein Original-ROM ins öffentliche Repo.

**Ausgabe:** Exakte Quell-/Test-IDs, dokumentierte Terminierung und Reproduktion, PASS/FAIL/NOT RUN einschließlich negativer Mutanten, eigene Logs/Messungen und getrennt **Bank-/Recall-Funktionalität**, **GUI-GO/NO-GO** und **RELEASE-GO/NO-GO**. Kein Codex-Fix im READ-ONLY-Audit.

**Bis dahin: GUI-NO-GO und RELEASE-NO-GO.**
