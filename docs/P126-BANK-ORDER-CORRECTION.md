# P126 — unified bank-event ordering, channel-local MIDI banks (candidate)

**Stand: 2026-11-05. GUI-NO-GO und RELEASE-NO-GO bleiben verbindlich.**

## Unabhängiger P125-Nachaudit (Code `805a2ef1`)

Der vom Projektinhaber übermittelte Codex-Nachaudit meldete **GUI-NO-GO / RELEASE-NO-GO**:

- Der ursprüngliche von P124 überlebende Audioblock-Fall (bereits laufendes `process`, Recall 0, danach Bank 5) wurde in P125 behoben.
- Die **umgekehrte Richtung** (ein zuerst gestarteter, pausierter Recall beendet sich **nach** einer angenommenen VST3-Bankänderung) scheitert weiterhin.
- Weitere **HOHE** Bankreihenfolgefehler verlieren Browseraufträge, verletzen MIDI-Kanaltrennung und können neuere Recalls überschreiben.
- `getTailSamples() == kInfiniteTail` wird korrekt gemeldet, jedoch ist ein hörbarer Chorus-Rest und ein mögliches ungünstiges Idle-Verhalten weiterhin separat zu prüfen.
- Lastprobleme bestehen weiter; in einem Wiederholungslauf gelangen nur **498/500** Host-Saves.

**Quellengrenze:** Die originalen externen Codex-Artefakte (`/tmp/P125-Nachaudit-805a2ef1.md` und `/tmp/P125-Nachaudit-Artefakte-805a2ef1.tar.gz`) wurden nur als Pfade aus der anderen Ausführungsumgebung übermittelt und lagen hier nicht vor. Daher werden keine neuen Fundstellen oder Einzelmessungen aus diesen Dateien erfunden. Dieser Abschnitt gibt exakt den übermittelten Auditstatus wieder.

## Neuer Korrekturkandidat

**Exakter Windows-getesteter C++-Commit:** [`713dcc8cf69a4a644809a5d9b305a7900aca73c0`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/713dcc8cf69a4a644809a5d9b305a7900aca73c0)

**GitHub Actions Windows 2022:** [Run #42086496250 – SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42086496250) (realer x64 VST3 Build, vorhandene native/VST3-Regressionsphase, Metadaten, EditorHost und Paketerstellung).

Betroffene Dateien:

- `src/vst3/BankOrder.h` **neu** — separate atomare Produzenten für Recall, Browser-Notification und Audio-Bankparameter mit einer gemeinsamen monotonen Ereignisnummer. Damit ist ein alter Recall nicht mehr bloß gegenüber dem Browser-Nachrichtenstempel, sondern auch gegenüber einem neueren gewöhnlichen Host-Bankparameter untergeordnet. Der Audiopfad benötigt dafür nur `fetch_add`/`store`, keine CAS-Spin-Schleife, keinen Mutex und keine Allokation.
- `src/vst3/Factory.cpp` — Ein Recall erhält seine Ereignisnummer **vor** Stream-Read und Engineaufbau. Beim Commit wird seine Bank nicht gegen neuere Browser-/Audio-Auswahlen durchgesetzt; die neueste globale Bank wird auf den gespeicherten State und die vorbereitete Engine angewandt. Host-Bankparameteränderungen werden vor einem eventuell scheiternden RT-Writer-Gate veröffentlicht und am nächsten Callback nachgeführt. Wiederholte konstante Automationspunkte werden nicht als neue GUI-Geste interpretiert. Die alte unbedingte Quittierung eines Browser-Snapshots durch MIDI-CC0/32 entfällt.
- `src/vst3/MidiLiveState.h` — MIDI CC0 und CC32 erhalten jeweils einen **Kanalstempel**. Ein globaler Bankwechsel verwirft nur ältere Bank-CC-Werte und spielt nur *neuere* CC-Werte des jeweiligen Kanals wieder ein. CC0/32 auf Kanal A dürfen weder die Browserbank aller anderen Kanäle überschreiben noch einen nachfolgenden Browserauftrag quittieren.
- `tests/p122_browser_bank_command.cpp` — neue Checks für beide zeitlichen Recallrichtungen, drei globale Bankquellen und ältere/neuere kanalbezogene Bank-CC-Werte.
- `tests/p122_vst3_bank_host.cpp` — weitere echte VST3-Processor-Regression: langsamer Bank-0-Recall, später erfolgreicher kBankID=5-Flush, Recall-Ende, Save unmittelbar und nach Folgeblock; späterer Bank-0-Recall muss zurückschalten können; zusätzlich CC0 auf MIDI-Kanal 3 vor einer neuen Browserbank 9. Der P125-Test der *umgekehrten* Reihenfolge bleibt erhalten.

**Bewusst unverändert:** historischer ROM-Zwang, 28-MiB-RAM-Grenze, SF2-DSP, Effekte, GUI, Projektformat V10, `kInfiniteTail`, OP(L)3-Module und Windows-VST3-Zielplattform. Keine Releasefreigabe.

## Unabhängiger P126-Nachaudit — verbindlicher READ-ONLY-Auftrag

Codex soll **ausschließlich** Code `713dcc8cf69a4a644809a5d9b305a7900aca73c0` prüfen. Keine vorhandenen Repositories/Branches/Commits/PRs ändern; eigene temporäre Fixtures/Proben außerhalb anlegen.

1. Die **originalen P125-Fails unverändert** wiederholen, besonders *beide* Richtungen mit pausiertem Audiogetter **und** pausiertem Recall-Stream. Normalen Browserpfad `PresetBrowserView::Select` mit echten Controller-PerformEdits statt nur künstlicher Binärnachricht prüfen. Nach jedem Ereignis tatsächlich klingende Bank, Browser-/Controllerzustand, gespeicherte V10-Bank **und Folgeblock** vergleichen.
2. **Kanaltrennung:** echte ROM-/synthetische SF2-Engine mit mindestens zwei verschieden klingenden Instrumenten/Bänken, MIDI CC0/CC32 auf mehreren Kanälen, dazwischen Browser 0/5/9 und Recall. Eine neuere kanalbezogene CC-Auswahl darf nicht den Browserauftrag quittieren oder andere Kanäle verändern. Eine neuere globale Bankauswahl soll nur ältere CC-Auswahlen überholen; neue CCs bleiben aktiv. Drumkanal-Konvention separat prüfen.
3. **Stempel-/Race-Analyse:** Stempelvergabe und Veröffentlichung auf Browserthread vs. Audiothread vs. Control-Recall durch gezielte Pausen in beiden Richtungen; alte Browserpublisher müssen neuere nicht zurücksetzen. Synthetische Negativmutationen (alte unbedingte Snapshot-Quittierung oder erneutes unbedingtes CC0-Clear) müssen FAIL erzeugen.
4. **Processing und Tail** unverändert weiter prüfen: strikter Lifecycle, `getTailSamples()`, PCM-Tail nach NoteOff inklusive Chorus/Room-Reverb, Host-Offlinerendering und Suspend/Idle-Verhalten. Das reine `kInfiniteTail`-API-PASS beseitigt keine hörbare Chorus-Restproblematik.
5. **Last- und Save-Verfügbarkeit:** gepactes 44,1-kHz/1024-Frames-Audio bei 1/16/30 Stimmen sowie dichter Pitch-/Programm-Automation und Recall; 500/500 gültige Saves als Ziel, keine falsch geglätteten Deadline-Metriken. Den gemeldeten 498/500-P125-Wiederholungslauf dokumentieren, die Ursache isolieren. Neue Bankänderungen dürfen weder RT-Allokation, RT-Mutex noch Blockierungs-/Retirement-Kosten hinzufügen.
6. P123/P124/P125-Regressionsmatrix einschl. 30.000 State-Roundtrips, korrekter Panzeitbasis, Browserfehler→Wiederverbindung, Engine-Reclamation und VST3-Lifecycle. Prüfe Negativkontrollen, nicht nur SDK-Rückgabewerte.

**Ausgabe:** Jeder Fall PASS/FAIL/NOT RUN mit präziser Reproduktion, Commit, Quellstelle, getrenntem Klang-/Save-/GUI-Ergebnis, Timing- und Sanitizer-Protokoll. **GUI-GO und RELEASE-GO getrennt beurteilen.** Original-ROM/Ziel-DAW und echte Windows-Mausinteraktion keinesfalls als ausgeführt ausgeben, wenn nur Linux-Adapter oder synthetische Assets geprüft wurden. Keinen Code ändern.

**Bis zu solch einer unabhängigen Abnahme: GUI-NO-GO / RELEASE-NO-GO.**
