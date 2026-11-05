# START HERE — 125A AWE Synthesizer

Stand: 2026-11-05. Dieses Dokument beschreibt den aktuellen **Entwicklungs-/Prüfstand**, keine Freigabe.

## Wo wird weiterentwickelt?

- Repository: `challanger2000/125A-AWE-Synthesizer`.
- Einziger aktiver Korrektur-Branch: `fix/p122-bank-dirty-audit`.
- Getesteter Quellcode: `1f351bb9cf1143ef1d0b8b9be30084ad034823fd`.
- Erfolgreicher Windows-Prüflauf: https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41960673095
- Binaries (Actions artifact): `125A-P122-Windows-x64-VST3`.
- GUI-Nachweise (Actions artifact): `125A-P122-EditorHost-GUI-Smoke`.
- `main` ist **nicht** der aktuelle Entwicklungsstand. Nicht ohne vollständige Abnahme übernehmen.

## Verifizierte P122-Prüfungen

- 32/32 CTests PASS, darunter `125A_p122_browser_bank_command` und `125A_p122_vst3_bank_host`.
- Steinberg VST3 Validator: 47/47 PASS.
- Windows EditorHost: 3/3 echte GUI-Durchläufe, Exitcode jeweils 0.
- Neu: ausdrückliche Bank-Neuauswahl über VST3-Controller/Prozessor-Nachricht. Die DAW kann einen unveränderten Bank-Parameterwert unterdrücken, die Nachricht aber nicht mit der gewöhnlichen Parameterqueue verwechseln.
- Normale konstante Bank-Automation löst **keine** wiederholte Browserbank-Übernahme aus, damit jüngere MIDI-CC0-Wahlen bestehen bleiben.
- Ablehnendes `IComponentHandler2::setDirty` führt nicht mehr zu unbegrenzten Wiederholungen.
- P121-Pitchbend-Fix und Synth-/86Box-PCM-Regression sind im Stand enthalten. Audiodaten in CI stammen aus einer synthetischen Test-ROM, nicht aus einem Original-ROM.

## Noch offen — Release NO-GO

1. Unabhängige **echte VST3-Audioautomation** mit Original-ROM und Original-SBK/SF2, insbesondere konstante vs. dichte Pitchbend-Queue bei Panbewegungen und 16 Stimmen.
2. Bankwechsel über MIDI-CC0, anschließend **erneute Auswahl derselben Browserbank im DAW-Host**: UI-Anzeige, erklingende Bank und Speicherzustand müssen übereinstimmen.
3. **Schließen des VST3-Editors/Prozessors während echter ausstehender ACK- und restartComponent-Nachrichten**. Der dreifache EditorHost-Smoke allein ist kein vollständiger Nachweis.
4. Bis zum GO keine Gold-GUI-Freigabe, kein Release-/Gumroad-Paket.

## Repository-Pflege

- Keine weiteren P-Branches für bloße Einzelkorrekturen anlegen. Fehler zunächst auf dem aktuellen Korrektur-Branch beheben.
- Frühere P120/P121-Stände und weitere übernommene Historie wurden als `archive/pre-p122-cleanup/*` Git-Tags erhalten.
- Historische offene Pull Requests nicht blind schließen oder Quell-/Zielbranches löschen.
- Keine originalen Creative-ROMs, SoundFonts oder anderen proprietären Daten in öffentliche Tests oder Pakete aufnehmen.

Dieses Dokument hat Vorrang gegenüber der veralteten P13-Einleitung, die zuvor in der README stand.
