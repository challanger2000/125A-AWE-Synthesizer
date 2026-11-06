# P132 — unabhängiger Windows-Echtzeit-Audit

Stand: 6. November 2026. **Separater Branch `audit/p132-realtime`. Kein Merge,
keine Releasefreigabe. Echtzeit-Zielrechnerabnahme: NOT RUN.**

## Ausgangspunkt und Fragestellung

Produktionsbasis: `c7d803c1b328166f6f5edcb770aa9c9f8b49ecda` auf
`fix/p122-bank-dirty-audit`. P131-Diagnose: PR #70,
`8fe01428741cb74070fe8b387e24b4b7e60613b5`, wurde gelesen, nicht gemergt.
P131 berichtete in einer Windows-VM keine Deadlinefehler, in älteren Messungen
jedoch Ausreißer. Sein Save+Recall-Fall hielt deutlich weniger NoteOn-Identitäten
als Render/Save. Rohzyklen sind keine präzisen CPU-Millisekunden.

P132 verändert zunächst **keine Produktionsdateien unter src/** und insbesondere
keine Chorusberechnung. Eine Korrektur darf erst einem nachgewiesenen Fehler
folgen. Der aktuelle Untersuchungsgegenstand ist die Qualität und kausale
Auswertung der Messung, kein vorweggenommener DSP-Optimierungsauftrag.

## Tatsächliche DLLs, musikalische Last und Kontrollmessung

- Die normale VST3 und eine **separat gelinkte vollständige diagnostische VST3**
  werden aus denselben Produktionsquellen gebaut. Die Diagnosekopie macht nur
  Felder sichtbar und fügt passive Exporte außerhalb von process() hinzu.
  Kein Timing-/Heap-Hook wird in den Audioprozessor eingefügt.
- In zwölf Kombinationen aus 128/256/512/1024 Frames und 1/16/30 Stimmen müssen
  beide DLLs mit derselben synthetischen ROM/SF2 **bitidentisches tatsächliches
  PCM** und dieselben V10-Streams liefern. Stille darf diesen Test nicht bestehen.
- Die diagnostische DLL zählt ohne Port-Lesezugriffe, Queue-Flush oder erneutes
  Rendern die tatsächlich belegten Synth-Slots und die Chip-Stimmen mit
  `cvcf_curr_volume != 0`. NoteOn-Identitäten und laufende Envelope-Engines sind
  zusätzliche Messwerte, kein Ersatz für diese körperliche Lastbeobachtung.
- Alle Fälle benutzen anfangs dasselbe melodische Preset (0,0), dieselben
  gehaltenen Tasten und dieselbe Anschlagstärke. Program-/Bankautomation ist ein
  eigener definierter Fall; gehaltene Noten werden dadurch nicht neu gestartet.

## Messmatrix und Recall-Kontrolle

44,1 kHz; 128/256/512/1024 Frames; 1/16/30 Stimmen; fünf Lastfälle:
Render, parallele Saves, parallele Saves+Recalls, Bank-/Programmautomation mit
Saves und dichte Pitchbend-/MIDI-/Master-/GUI-Automation mit Saves+Recalls.
Normalerweise 600 gemessene Blöcke je Zelle; bei 128 Frames / 30 Stimmen für
Render/Save/Save+Recall jeweils 3.000. Zwei Durchläufe pro Windows-Zuteilung,
mit/ohne CPU-ETW in umgekehrter Reihenfolge auf zwei unabhängigen Windows-Jobs.

Ein neuer Recall erhält seinen Intentstempel vor einer kontrollierten ersten
Streamlesepause. Neue Noten werden anschließend angenommen und aufgewärmt,
bevor der Control-Thread mit der Vorbereitung und Veröffentlichung fortfährt.
Das verhindert den ungeprüften P131-Vergleich von 12 gegen 32 gehaltene Noten.
Es ist eine **Labor-Lastkontrolle**, kein realer DAW-/ASIO-Callback-Ablauf.

Jede Seed-/Warmup-Ausführung wird ebenfalls als tatsächlicher Prozessaufruf
protokolliert. Diese Aufrufe, ihre CPU-Arbeit und ein bewusst neu angesetzter
Host-Pacing-Zeitpunkt dürfen nicht als normale Deadlineabnahme verkauft werden.
Bei Engineveröffentlichung verbleiben Anlauf-/Übergangsblöcke. Deshalb werden
zwei Populationen ausgegeben:

1. **Alle gemessenen Blöcke**, mit sämtlichen Deadlinefehlern, auch wenn die
   Stimmenzahl abweicht oder die Enginegeneration wechselt.
2. **Lastgleiche Blöcke**, nur mit geforderter Zahl tatsächlich belegter und
   nicht stummer Chip-Stimmen vor und nach dem Callback sowie gleicher
   Enginegeneration. Unterfüllung und Generationswechsel werden ausdrücklich
   gezählt; schlechtere Blöcke werden nicht aus dem Gesamtbefund entfernt.

## Zeitbasis, ETW, Heap und Nachweisgrenzen

- QPC direkt um IAudioProcessor::process(): Walltime in Mikrosekunden.
  Geplanter Start und Wakeup-/Host-Vorbereitungsverzögerung sind getrennt.
- QueryThreadCycleTime: nur Rohzyklen, keine Umrechnung anhand angenommener GHz.
  GetThreadTimes dient lediglich der gesamten Case-Thread-Bilanz inklusive
  Hostarbeit, ausdrücklich nicht einer feingranularen DSP-Zeit je Callback.
- WPR CPU erfasst, soweit verfügbar, CSwitch- und Samplingereignisse. Ein
  nativer TDH-Decoder hält Roh-QPC-Zeitstempel bei, verknüpft nur die tatsächliche
  Prozess-Thread-ID und löst verfügbare Diagnosesymbole über die PDB auf.
- Bekannte Sleep-/Busy-Intervalle prüfen Zeitbasis und Kontextwechsel-Abdeckung.
  ETW-Datenverlust oder fehlende Kalibrierung bedeuten NOT RUN für kausale
  Attribution. Ohne diesen Nachweis wird aus einer Walltime-Spitze keine
  Scheduler-, Mutex- oder DSP-Ursache erfunden.
- Nachgewiesenes Ready-Off-CPU kann eine Budgetüberschreitung allein erklären.
  Waiting-Off-CPU benötigt zusätzlich Stack-/Wait-Grundprüfung. Geplante
  On-CPU-Zeit ist immer noch **nicht reine DSP-Rechenzeit**: Kernel-/ISR-/DPC-
  und Bibliotheksanteile können darin verbleiben. Sampling zeigt Hotspots,
  ersetzt keine exakte Funktionslaufzeit.
- Separater WPR-Heap-Durchlauf, soweit verfügbar, mit bekannten malloc(37),
  realloc(73), HeapAlloc(91), HeapReAlloc(131) außerhalb von process(). Erst
  vollständig erkannte Kontrollgrößen und verlustfreie Trace erlauben einen
  Heap-Backend-Befund. Fehlende Profile/Ereignisse werden nicht als Nullbefund
  bezeichnet. Diese Heap-Messung ist kein unbeeinflusster Performancevergleich.
- ETL-Dateien für WPA, rohe Callback-, CSwitch-, Heap-, Sampling- und
  Qualifikationsdaten bleiben im CI-Artefakt. WPA-GUI/ASIO auf dem Zielrechner
  ist NOT RUN. Treiber-/DPC-/CPU-Frequenzursachen sind ohne passenden Nachweis
  ebenfalls keine festgestellten Softwarefehler.

## Regressionen und Ausführung

`-D125A_P132_AUDIT=ON -D125A_BUILD_VST3=ON` aktiviert ausschließlich die separate
Diagnostik. Der normale Build bleibt bestehen. Der vorhandene P131-Fix für einen
von MSBuild mehrfach gleichzeitig geschriebenen Testheader wurde als reine
Test-Build-Abhängigkeit übernommen. Die bestehende P130-C++-Heap-Regression wird
unverändert ausgeführt.

Die Windows-Workflows `p132-windows-audit.yml` und
`p132-repeat-windows-audit.yml` bauen beide DLLs, führen die vollständigen
CTests, explizit den normalen 47/47-Validator und drei EditorHost-Smokes aus.
Sie erfassen zwei separate Runner-Zuteilungen mit vertauschter Reihenfolge.
Ihre Ergebnisse sind bis zur tatsächlichen Auswertung **NOT RUN**, nicht PASS.
Ein grüner Workflow bedeutet auch danach keine Echtzeitfreigabe.

**Offene Abschlussentscheidung:** Echtzeit NOT RUN mangels Zielrechnernachweis;
konkrete Windows-Reproduktionen und ihre belegbaren Ursachen werden nach den
Messläufen ergänzt. Keine spekulativen Produktions- oder Chorusänderungen.
