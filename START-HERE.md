# START HERE — 125A AWE Synthesizer

Stand: 2026-11-05. Dieses Dokument beschreibt den aktuellen **Entwicklungs-/Prüfstand**, keine Freigabe.

## Wo wird weiterentwickelt?

- Repository: `challanger2000/125A-AWE-Synthesizer`.
- Einziger aktiver Korrektur-Branch: `fix/p122-bank-dirty-audit`.
- **Aktuell getesteter P124-Codecommit:** `2f0c4d225f41f51c1b37d3c04986845024c0f80f`.
- Erfolgreicher Windows-Prüflauf: https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42060246071
- Binaries (Actions artifact): `125A-P122-Windows-x64-VST3`.
- GUI-Nachweise (Actions artifact): `125A-P122-EditorHost-GUI-Smoke`.
- `main` ist **nicht** der aktuelle Entwicklungsstand. Nicht ohne vollständige Abnahme übernehmen.

## Verifizierte Windows-Prüfungen am P124-Kandidaten (kein GUI-GO)

- 34/34 CTests PASS, darunter `125A_p122_browser_bank_command`, `125A_p122_vst3_bank_host` und `125A_p122_host_shutdown`.
- Steinberg VST3 Validator: 47/47 PASS.
- Windows EditorHost: 3/3 echte GUI-Durchläufe, Exitcode jeweils 0.
- Neu: ausdrückliche Bank-Neuauswahl über VST3-Controller/Prozessor-Nachricht. Die DAW kann einen unveränderten Bank-Parameterwert unterdrücken, die Nachricht aber nicht mit der gewöhnlichen Parameterqueue verwechseln.
- Normale konstante Bank-Automation löst **keine** wiederholte Browserbank-Übernahme aus, damit jüngere MIDI-CC0-Wahlen bestehen bleiben.
- Ablehnendes `IComponentHandler2::setDirty` führt nicht mehr zu unbegrenzten Wiederholungen. `restartComponent(kLatencyChanged)` wird bei Ablehnung höchstens dreimal pro Änderung versucht. Win32-Dispatcher-Shutdown mit noch ausstehendem Timer wird separat getestet.
- P121-Pitchbend-Fix und Synth-/86Box-PCM-Regression sind im Stand enthalten. Audiodaten in CI stammen aus einer synthetischen Test-ROM, nicht aus einem Original-ROM.
- Der unabhängige P123-Codex-Nachaudit **bestätigte alle vier P123-Korrekturen**, einschließlich 30.000 Processor-Roundtrips und 500/500 Saves mit tatsächlich klingender Einzelstimme. Zwei neue HOHE Fehler blieben: ein später angenommener Bank-5-Auftrag wurde von einem älteren Recall überschrieben, und `setProcessing(true/false)` lieferte `kNotImplemented`. **P124** korrigiert beides; [Korrekturdokumentation und erneute Prüfaufträge](docs/P124-RECALL-PROCESSING-CORRECTION.md). Original-ROM und Ziel-DAW bleiben NOT RUN.

## Noch offen — Release NO-GO

1. Unabhängige **echte VST3-Audioautomation** mit Original-ROM und Original-SBK/SF2, insbesondere konstante vs. dichte Pitchbend-Queue bei Panbewegungen und 16 Stimmen.
2. Bankwechsel über MIDI-CC0, anschließend **erneute Auswahl derselben Browserbank im DAW-Host**: UI-Anzeige, erklingende Bank und Speicherzustand müssen übereinstimmen.
3. Die Win32-Timer-Shutdown-Regression ist bestanden; ein **Host-Integrationstest mit echtem ausstehendem ACK und restartComponent** in der Ziel-DAW bleibt für Release-Abnahme offen.
4. **GUI-Start — AUSDRÜCKLICH NO-GO:** Alle vier P123-Korrekturen wurden inzwischen von Codex unabhängig bestätigt, aber der P123-Nachaudit fand zwei neue hohe Fehler bei späteren Bankbefehlen und `setProcessing`. P124 besteht den Windows-VST3-Build, 34/34 CTests, 47/47 Validator und 3/3 EditorHost. **Ein erneuter unabhängiger Codex-Nachaudit des exakten P124-Codes ist noch NOT RUN.** Originalhardware-Klanggleichheit ist dafür nicht erforderlich.
5. **Release NO-GO:** Vor finalem Release sind weiterhin die echten ROM-/SF2-Audio- und DAW-Abnahmetests erforderlich; kein Release-/Gumroad-Paket vor GO.

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
