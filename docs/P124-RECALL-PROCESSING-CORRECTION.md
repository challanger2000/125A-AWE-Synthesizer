# P124 — Bank-Reihenfolge und VST3-Processing-Lebenszyklus

**Korrekturkandidat, kein GUI-GO, kein Release-GO. Stand: 2026-11-05.**

- **Branch:** `fix/p122-bank-dirty-audit`
- **Exakt Windows-getesteter Quellcode:** [`2f0c4d225f41f51c1b37d3c04986845024c0f80f`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/2f0c4d225f41f51c1b37d3c04986845024c0f80f)
- **Windows Actions #42060246071:** [34/34 CTests, 47/47 Steinberg Validator, 3/3 EditorHost](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42060246071) PASS. Die neuen realen VST3-Regressionen `125A_p122_browser_bank_command` und `125A_p122_vst3_bank_host` PASS.
- Keine proprietären ROMs oder SoundFonts im Repository/CI; Originalasset-/Studio-Pro-Ziel-DAW-Abnahme **NOT RUN**.

## Unabhängiger Codex-Nachaudit zu P123 (Code d91fa26b)

Codex bestätigte die vier P123-Korrekturen (darunter 30.000 Processor-Roundtrips und 500/500 Saves mit einer klingenden Stimme) und fand **zwei neue HOHE Fehler**:

1. Ein neuer Browserbank-Befehl für Bank 5, der während eines schon laufenden älteren Recalls angenommen wurde, konnte durch dessen späteren Bank-0-Auftrag überschrieben werden. Zudem konnte `process()` einen Bankauftrag bereits als konsumiert markieren, obwohl die Recall-Schreibsperre dessen Anwendung verhinderte.
2. `IAudioProcessor::setProcessing(true/false)` lieferte das SDK-Basisklassenresultat `kNotImplemented`; ein strenger Host scheitert am normalen Activated/Processing-Lebenszyklus.

## P124-Kandidatenkorrekturen

`BrowserBankCommand` erfasst nun den Kommando-Stamp bei Eintritt in `setState`; der Recall darf seine Bank nur mittels bedingtem CAS veröffentlichen, sofern seitdem kein neuerer Auftrag akzeptiert wurde. Andernfalls bleibt die neuere Bank sowohl im Recall-State als auch in der vorbereiteten Engine erhalten. Der Audio-Callback erwirbt zuerst den nichtblockierenden RT-Writer; nur nach erfolgreichem Erwerb darf er den Auftrag konsumieren. `Processor::setProcessing` antwortet mit `kResultOk` in konstantem, lock- und allokationsfreiem Host-Handshake; Midi-Stimmen-/Tail-Verhalten bei Stop/Start muss unabhängig kontrolliert werden.

**Gezielte Tests:** Der echte VST3-Processor liest einen absichtlich pausierten V10-MemoryStream. Während der ältere Bank-0-Recall schon begonnen hat, wird Bank 5 angenommen; nach Abschluss und `process` muss `getState` Bank 5 melden. Gegentest: neuer Recall 0 überschreibt einen tatsächlich früher angenommenen Bank-7-Auftrag. Test der RTCAS-Kollision ohne verlorenes Consume. Verbindlicher VST3-Ablauf `setupProcessing -> setActive(true) -> setProcessing(true) -> process -> setProcessing(false) -> setProcessing(true/false) -> setActive(false)`; auch wiederholtes Start/Stop ohne intervenierendes process.

## Noch ausstehende unabhängige Abnahme (NO-GO)

**Codex soll rein lesend exakt den oben genannten C++-Commit erneut auditieren** und die beiden eigenen ursprünglichen N1/N2-Fälle unabhängig wiederholen. Prüfe Bank-0-/Bank-5-Reihenfolge mit echtem, verzögertem `setState`, getState-Roundtrip, mehrere schnell folgende Bankbefehle und parallele Recall-Audiogates. Prüfe strict VST3 `setProcessing` inklusive wiederholter Processing-/Aktivierungsübergänge, echten Audio-Callbacks, CPU/Echtzeit und Stimm-/Tail-Semantik; keine zeitaufwendige Arbeit in `setProcessing`. Die vier bereits behobenen P123-Fälle sind auf Regression zu prüfen: 30.000 Recall-/Audio-Roundtrips, 500/500 Saves mit einer klingenden Stimme, 44,1/48/96-kHz-Pan-Taktung, Browserfehler → Wiederverbindung.

Für jeden Test **PASS / FAIL / NOT RUN** angeben, inklusive Fundstellen, Reproduktion, Messung und Gegenbeispielen. Keine Änderungen/Commits/PRs durch Codex. **GUI und Release bleiben NO-GO** bis zur erneuten unabhängigen Prüfung. Originalhardware-Klanggleichheit allein ist keine GUI-Voraussetzung.
