# START HERE — 125A AWE Synthesizer

Stand: 2026-11-05. Dieses Dokument beschreibt den aktuellen **Entwicklungs-/Prüfstand**, keine Freigabe.

## Wo wird weiterentwickelt?

- Repository: `challanger2000/125A-AWE-Synthesizer`.
- Einziger aktiver Korrektur-Branch: `fix/p122-bank-dirty-audit`.
- **Aktueller Windows-getesteter P125-Korrekturkandidat:** `805a2ef1d49133aae022256161c275240ac80fed`. **Unabhängiges Codex-GO noch NOT RUN.**
- Vorheriger P124-Code `2f0c4d225f41f51c1b37d3c04986845024c0f80f`: **unabhängiger Nachaudit FAIL / GUI-NO-GO**, trotz vorheriger grüner Windows-Tests.
- Aktueller erfolgreicher Windows-Prüflauf: https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42069200394
- Binaries (Actions artifact): `125A-P122-Windows-x64-VST3`.
- GUI-Nachweise (Actions artifact): `125A-P122-EditorHost-GUI-Smoke`.
- `main` ist **nicht** der aktuelle Entwicklungsstand. Nicht ohne vollständige Abnahme übernehmen.

## Verifizierte Windows-Prüfungen am P125-Kandidaten (weiterhin kein GUI-GO)

- Windows-Build und komplette native/VST3-Testphase **PASS** (Actions #42069200394), darunter die um eine **späte Bank-5-Parameterqueue bei bereits laufendem Callback und dazwischenliegendem Bank-0-Recall** erweiterte `125A_p122_vst3_bank_host`-Regression; der Zustand muss vor/nach dem Folgeblock Bank 5 bleiben. Außerdem testet sie den späteren absichtlichen Rückwechsel auf Bank 0 und die nichtnullige Tail-Meldung.
- Steinberg VST3 Validator: 47/47 PASS.
- Windows EditorHost: 3/3 echte GUI-Durchläufe, Exitcode jeweils 0.
- Neu: ausdrückliche Bank-Neuauswahl über VST3-Controller/Prozessor-Nachricht. Die DAW kann einen unveränderten Bank-Parameterwert unterdrücken, die Nachricht aber nicht mit der gewöhnlichen Parameterqueue verwechseln.
- Normale konstante Bank-Automation löst **keine** wiederholte Browserbank-Übernahme aus, damit jüngere MIDI-CC0-Wahlen bestehen bleiben.
- Ablehnendes `IComponentHandler2::setDirty` führt nicht mehr zu unbegrenzten Wiederholungen. `restartComponent(kLatencyChanged)` wird bei Ablehnung höchstens dreimal pro Änderung versucht. Win32-Dispatcher-Shutdown mit noch ausstehendem Timer wird separat getestet.
- P121-Pitchbend-Fix und Synth-/86Box-PCM-Regression sind im Stand enthalten. Audiodaten in CI stammen aus einer synthetischen Test-ROM, nicht aus einem Original-ROM.
- **Neu in P125:** Verzögerte P124-Recall-Bankkommandos werden von später angenommenen Bankparametern bzw. CC0/CC32 überholt; der Browser-Epoch wird für spät eintreffende MIDI-Bankdaten erneut abgeglichen. `getTailSamples()` meldet konservativ `kInfiniteTail` statt fälschlich 0. Die echte Originalhardware-Tail- und Ziel-DAW-Prüfung ist **NOT RUN**.
- Der unabhängige P123-Codex-Nachaudit **bestätigte alle vier P123-Korrekturen**, einschließlich 30.000 Processor-Roundtrips und 500/500 Saves mit tatsächlich klingender Einzelstimme. Zwei neue HOHE Fehler blieben: ein später angenommener Bank-5-Auftrag wurde von einem älteren Recall überschrieben, und `setProcessing(true/false)` lieferte `kNotImplemented`. **P124** korrigierte die zunächst bekannten Reproduktionen, aber der **unabhängige P124-Nachaudit fand erneut den Bankfehler bei bereits gestartetem Audio-Callback (FAIL)**. Processing-Handshake ist dagegen **PASS**. **P125** korrigiert die neue Reihenfolge und die fehlende Tail-Meldung; [P125-Befund, Änderungen und exakter unabhängiger Prüfauftrag](docs/P125-LATE-BANK-TAIL-CORRECTION.md). Original-ROM und Ziel-DAW bleiben NOT RUN.

## Noch offen — Release NO-GO

1. Unabhängige **echte VST3-Audioautomation** mit Original-ROM und Original-SBK/SF2, insbesondere konstante vs. dichte Pitchbend-Queue bei Panbewegungen und 16 Stimmen.
2. Bankwechsel über MIDI-CC0, anschließend **erneute Auswahl derselben Browserbank im DAW-Host**: UI-Anzeige, erklingende Bank und Speicherzustand müssen übereinstimmen.
3. Die Win32-Timer-Shutdown-Regression ist bestanden; ein **Host-Integrationstest mit echtem ausstehendem ACK und restartComponent** in der Ziel-DAW bleibt für Release-Abnahme offen.
4. **GUI-Start — AUSDRÜCKLICH NO-GO:** Alle vier P123-Korrekturen wurden unabhängig bestätigt. Der unabhängige **P124-Nachaudit des exakten `2f0c4d2` ist durchgeführt und im Bank-Recall FAIL**, obwohl Processing-Lifecycle PASS. P125 (`805a2ef1`) hat den kompletten Windows-Workflow bestanden; **sein erneuter unabhängiger Codex-Nachaudit ist NOT RUN**. Teste unbedingt die vom P124-Audit ausgeführte gesperrte Audioqueue, Recall 0, Bank 5 über kBankID **und CC0/CC32**, Zustand/Folgeblock und tatsächliche klingende Bank. Originalhardware-Klanggleichheit ist für den GUI-Start nicht allein erforderlich.
5. **Release NO-GO:** Im P124-Audit blieben unter hoher Last Deadline-Überschreitungen und eine Save-Abweisung. Die P125-Windows-Prüfung allein hebt diese Befunde nicht auf. Zusätzlich stehen unabhängiger P125-Nachaudit sowie echte ROM-/SF2-Audio- und Ziel-DAW-Abnahmetests aus; kein Release-/Gumroad-Paket vor GO.

## Nach der klassischen Version — ausdrücklich zurückgestellte Erweiterungen

- **Nicht jetzt beginnen:** [Extended AWE Sampler — vorgemerkter Entwicklungsabschnitt](docs/FUTURE-EXTENDED-AWE-SAMPLER.md).
- Gewünscht: **direkter WAV-Import**, später Multisampling/Velocity-Zonen, Loop-Editor und eigene Presets; **Sample-Speicher bis 1 GiB** als technisches Forschungsziel (24-Bit-EMU8000-Adressraum bisher kein direkter 1-GiB-RAM).
- Die Reihenfolge ist verbindlich: erst P124/independenter Audit, dann die originale EMU8000-Effektimplementierung, optional fertige GUI und Classic-Abnahme, **erst anschließend** Extended-Entwicklung. **Classic bleibt mit ROM-Pflicht/28 MiB unverändert.**
- Keine aktuellen C++-Implementierungen oder eigenmächtige Scope-Erweiterung aufgrund dieser Notiz.

## Repository-Pflege

- Keine weiteren P-Branches für bloße Einzelkorrekturen anlegen. Fehler zunächst auf dem aktuellen Korrektur-Branch beheben.
- Frühere P120/P121-Stände und weitere übernommene Historie wurden als `archive/pre-p122-cleanup/*` Git-Tags erhalten.
- Historische offene Pull Requests nicht blind schließen oder Quell-/Zielbranches löschen.
- Keine originalen Creative-ROMs, SoundFonts oder anderen proprietären Daten in öffentliche Tests oder Pakete aufnehmen.

Dieses Dokument hat Vorrang gegenüber der veralteten P13-Einleitung, die zuvor in der README stand.
