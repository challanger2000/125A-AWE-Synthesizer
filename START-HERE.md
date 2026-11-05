# START HERE — 125A AWE Synthesizer

Stand: 2026-11-05. Dieses Dokument beschreibt den aktuellen **Entwicklungs-/Prüfstand**, keine Freigabe.

## Wo wird weiterentwickelt?

- Repository: `challanger2000/125A-AWE-Synthesizer`.
- Einziger aktiver Korrektur-Branch: `fix/p122-bank-dirty-audit`.
- Getesteter Quellcode: `d8b0af795dddd86594ef7076b061f75b65340fee`.
- Erfolgreicher Windows-Prüflauf: https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42035683374
- Binaries (Actions artifact): `125A-P122-Windows-x64-VST3`.
- GUI-Nachweise (Actions artifact): `125A-P122-EditorHost-GUI-Smoke`.
- `main` ist **nicht** der aktuelle Entwicklungsstand. Nicht ohne vollständige Abnahme übernehmen.

## Verifizierte P122-Prüfungen

- 34/34 CTests PASS, darunter `125A_p122_browser_bank_command`, `125A_p122_vst3_bank_host` und `125A_p122_host_shutdown`.
- Steinberg VST3 Validator: 47/47 PASS.
- Windows EditorHost: 3/3 echte GUI-Durchläufe, Exitcode jeweils 0.
- Neu: ausdrückliche Bank-Neuauswahl über VST3-Controller/Prozessor-Nachricht. Die DAW kann einen unveränderten Bank-Parameterwert unterdrücken, die Nachricht aber nicht mit der gewöhnlichen Parameterqueue verwechseln.
- Normale konstante Bank-Automation löst **keine** wiederholte Browserbank-Übernahme aus, damit jüngere MIDI-CC0-Wahlen bestehen bleiben.
- Ablehnendes `IComponentHandler2::setDirty` führt nicht mehr zu unbegrenzten Wiederholungen. `restartComponent(kLatencyChanged)` wird bei Ablehnung höchstens dreimal pro Änderung versucht. Win32-Dispatcher-Shutdown mit noch ausstehendem Timer wird separat getestet.
- P121-Pitchbend-Fix und Synth-/86Box-PCM-Regression sind im Stand enthalten. Audiodaten in CI stammen aus einer synthetischen Test-ROM, nicht aus einem Original-ROM.
- Nach dem unabhängigen Codex-Audit am 4c46500-Stand wurden fünf konkrete Befunde im P122-Branch bearbeitet: Zero-Sample-Pitchbend, RPN-Retuning, blockunabhängige Pan-Gleitzeit, konsistenter getState-Snapshot und sichtbare Browserbank-Fehlermeldung. Tests einschließlich des realen VST3-Programmspeicher-Stresstests PASS. Details: [docs/P122-CODEX-AUDIT-NACHPROBE.md](docs/P122-CODEX-AUDIT-NACHPROBE.md).

## Noch offen — Release NO-GO

1. Unabhängige **echte VST3-Audioautomation** mit Original-ROM und Original-SBK/SF2, insbesondere konstante vs. dichte Pitchbend-Queue bei Panbewegungen und 16 Stimmen.
2. Bankwechsel über MIDI-CC0, anschließend **erneute Auswahl derselben Browserbank im DAW-Host**: UI-Anzeige, erklingende Bank und Speicherzustand müssen übereinstimmen.
3. Die Win32-Timer-Shutdown-Regression ist bestanden; ein **Host-Integrationstest mit echtem ausstehendem ACK und restartComponent** in der Ziel-DAW bleibt für Release-Abnahme offen.
4. **GUI-Start:** Die vier hohen Codex-Befunde sind code-seitig bearbeitet und die gezielten Windows-Regressionen bestanden; ein unabhängiger Codex-Nachaudit des neuen HEAD steht noch aus. Keine Originalhardware-Klanggleichheit als GUI-Voraussetzung verlangen.
5. **Release NO-GO:** Vor finalem Release sind weiterhin die echten ROM-/SF2-Audio- und DAW-Abnahmetests erforderlich; kein Release-/Gumroad-Paket vor GO.

## Repository-Pflege

- Keine weiteren P-Branches für bloße Einzelkorrekturen anlegen. Fehler zunächst auf dem aktuellen Korrektur-Branch beheben.
- Frühere P120/P121-Stände und weitere übernommene Historie wurden als `archive/pre-p122-cleanup/*` Git-Tags erhalten.
- Historische offene Pull Requests nicht blind schließen oder Quell-/Zielbranches löschen.
- Keine originalen Creative-ROMs, SoundFonts oder anderen proprietären Daten in öffentliche Tests oder Pakete aufnehmen.

Dieses Dokument hat Vorrang gegenüber der veralteten P13-Einleitung, die zuvor in der README stand.
