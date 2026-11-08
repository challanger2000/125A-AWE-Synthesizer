# P170/P171 — dauerhafte numerische Prüfnachweise

Geprüfter Produkt-/Testquellstand:
`b02e02d472544eb2122533f9b8d7dc9d0b97f68a`.
Alte PCM-Referenz: P169 `99fb90fc855c4c7643e24816fa644fdc738c290f`.
Methodik, Ursachen und offene Grenzen stehen im
[Korrekturbericht](../../P170-P171-AUDIO-CORRECTIONS.md).

Diese Ablage enthält nur Text, numerische Messwerte und Hashes synthetischer
Testsignale. Keine Original-ROM, SoundFont, Treiber oder private Aufnahme.
Die eigentlichen synthetischen PCM-Ausgaben und ETL bleiben in den angegebenen
Windows-QA-Artefakten; ihre Prüfanordnung ist im Repository reproduzierbar.

- `local-provenance.json`: exakte Basis, Compiler, Testzahlen, Sanitizeroptionen
  und ausdrücklich ausgeschlossene Bereiche.
- `native-ctest.txt`: vollständige 53/53-Regression; `native-last-test.log.gz`
  enthält zusätzlich die Einzelassertionen, Pegel und Callback-Ausgaben.
- `awe-asan-ubsan-lsan-ctest.txt` und `awe-sanitized-last-test.log.gz`:
  39/39 AWE-Tests mit aktiver ASan-/UBSan-/Leak-Erkennung. Kein TSAN-Ergebnis.
- `native-audio-measurements.json.gz`: 116 synthetische Fälle mit Stimuli,
  Registerabbildern, RMS/Spektral-/Dauerwerten und SF2-/PCM-SHA-256;
  40 Signalentscheidungen bestanden.
- `p169-paired-comparison.json` und `p169-before-measurements.json.gz`:
  identische Stimuli, 24 alte fehlschlagende Signalentscheidungen und
  21 unbetroffene Neutralfälle mit 11.782.800 bitgleichen PCM-Bytes.
- `p167-*-before.txt`: ursprünglicher Kanal-10-Fehler mit akustischer
  Gegenkontrolle. `release-fallback-before-*` und `midi-send-before-*` zeigen
  zusätzliche während der Selbstgegenprüfung reproduzierte Fehler vor Korrektur.
- `negative-*-stdout.txt` und `negative-*-measurements.json.gz`: acht
  absichtlich fehlerhafte Testvarianten. Ihre gezielten Audio-FAILs sind der
  erwartete Nachweis der Fehlererkennung. Crash oder Setupfehler wäre kein PASS.
- `windows-*-summary.json`: originale SHA-verifizierte Windows-Summaries,
  jeweils 62/62 CTests, 537/537 Modulvalidator, 99 GUI-Entscheidungen und
  Test-Lab-Status samt tatsächlichem DLL-Hash. Alle 72 Callbackzellen mit
  Median/p99/Max/Misses/Held-Min/Max, acht Negativkontrollen und PCM-Vergleich.
  Ihr damaliges `etw.analyzed=false` bleibt als Originalbeleg unverändert;
  die späteren `*-etw-analysis.json` belegen die nachfolgende Auswertung.
- `windows-*-steps.json`: öffentliche Schrittstatus der tatsächlichen Jobs;
  drei GUI-Smokes sind zusätzlich zu den 99 ausführlichen Entscheidungen belegt.
- `windows-*-callbacks.csv.gz`: sämtliche 14.400 ursprünglichen Callbackzeilen
  je Lauf, ohne Auslassung; nach Dekompression exakt der zuvor veröffentlichte
  CSV-SHA-256. Alle 72 Statistiken wurden daraus lokal nochmals nachgerechnet.
- `windows-*-etw-analysis.json` und `windows-*-etw-control.json`: kalibrierte
  Analyse der ursprünglichen GeneralProfile-Traces. Beide 0 Event-/Bufferverluste,
  alle 28.800 Callbackfenster abgedeckt. Ein Miss: 3.959,1 µs QPC-Fenster,
  1.494,2 µs eingeplant und 2.464,9 µs Ready-Off-CPU; Preemption reicht als
  Erklärung. Kein reiner DSP- oder vollständiger Heapnachweis.
- `windows-*-etw-steps.json`: tatsächliche ursprüngliche Decoder-/Kontrolljobs.
  `windows-artifacts.json`: Namen, Größen, IDs und veröffentlichte Paketdigests.
- `legacy-cqm-sanitized-tests.txt.gz`: separate historische CQM-UB, FAIL.
  `sdk-sanitized-validator-leaks-build.txt.gz`: externer SDK-Tool-Selbsttest mit
  6.124 Leak-Bytes/95 Objekten, FAIL. Beide bleiben sichtbar und werden durch
  den engeren 39/39-AWE-PASS nicht nachträglich als fehlerfrei ausgegeben.

Gzip-Dateien sind normale unveränderte UTF-8-/CSV-Rohdaten nach Dekompression,
zum Beispiel mit `gzip -dc DATEI.json.gz`. Dateiintegrität wird in
`SHA256SUMS` festgehalten. Die Quellen der Audioorakel, Mutationen und des
ungeänderten P169-Vergleichs stehen unter `tests/p170_*`; die Windows-Matrix
unter `.github/workflows/p170-p171-audio-windows.yml`.

Der neue Callback-Stress misst den quellidentisch extrahierten Processor im
Testprogramm. Er ist kein Zeitnachweis der exportierten Produkt-DLL und kein
physischer ASIO-/DAW-Nachweis. Der gesonderte Windows-DLL-Host prüft deren
First-Note-Funktion. Originalmedien, physischer Zielrechner, vollständige
Windows-Heapattribution und zweiter Auditor: NOT RUN.
Adversarialer Produktreview: SELF-CHALLENGE. FULL AUDIT: NOT COMPLETE.
Kommerzielle Freigabe: NO-GO.

[Windows-Funktionsprüfung 42479356487: SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42479356487),
[kausaler ETW-Nachaudit 42480859178: SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42480859178).
Auditcode `dce06d3d3de3517082588800f4706e96cd619a5d` ausschließlich auf dem
separaten Auditbranch. Beide Original-CSV-SHA-256 stehen in den Summaries.
Deadlinefreie Matrix: **FAIL (1/28.800)**. Physische Echtzeitabnahme: **NOT RUN**.

Vollständige Roh-CSV-Sicherung:
[42481489720](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42481489720),
Audit-/Publikationsstand `93441628edc0c5d9bb341c9f5f423dab2914ea8c`.
Die zusätzliche Partitionierung berücksichtigt die öffentliche GitHub-Grenze
von 4.096 Zeichen je Annotationsnachricht und zehn Notices pro Schritt.
Alle Stücke wurden zusammengefügt, dekomprimiert und gegen die bereits vor
Auswertung feststehenden Original-Hashes geprüft:

- A: `3e00913b25ab17eb7c0310140fcb3e7823b37712201d7fb7261470fe5f8852fe`
- B: `0c93af66a70e9043144ea58f616c2c51987f5ced5eb108e77fd7e3a511cba543`
