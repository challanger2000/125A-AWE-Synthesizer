# P132 — unabhängiger Windows-Echtzeit-Audit

Stand: 6. November 2026. **Separater Branch `audit/p132-realtime`.**
**Echtzeiturteil: FAIL im Windows-Labor.** Zielrechner-/ASIO-Abnahme: **NOT RUN**.
Kein Merge und keine Releasefreigabe.

## Ausgangspunkt und Fragestellung

Produktionsbasis: `c7d803c1b328166f6f5edcb770aa9c9f8b49ecda` auf
`fix/p122-bank-dirty-audit`. P131-Diagnose: PR #70,
`8fe01428741cb74070fe8b387e24b4b7e60613b5`, wurde gelesen, nicht gemergt.
P131 berichtete in einer Windows-VM keine Deadlinefehler, in älteren Messungen
jedoch Ausreißer. Sein Save+Recall-Fall hielt deutlich weniger NoteOn-Identitäten
als Render/Save. Rohzyklen sind keine präzisen CPU-Millisekunden.

Der erste Messstand `418cc6b580a8cb3fd770b33b3804e0626d3c08f8` veränderte keine
Produktionsdateien unter src/. Erst nach nachgewiesenen periodischen
980-Frame-Arbeitsbursts wurde ausschließlich `src/engine/Emu8000Box.cpp`
korrigiert: Zwischenfortschritt des vorhandenen Chiprenderers im
128-Chipframe-Raster; derselbe 980-Frame-FIFO und dieselbe DSP-/Chorusberechnung.
Der Windows-Vorher-/Nachher-Nachweis bestätigt die Abflachung dieser Spitzen.
Andere Deadlineüberschreitungen bestehen weiterhin; sie sind nicht pauschal
als Scheduling- oder DSP-Fehler erklärt.

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

Die ersten Windows-Stressversuche brachen korrekt an der physischen
Stimmenkontrolle ab, während 43/43 CTests, Validator und GUI-Smokes bestanden.
Die ursprünglich dafür benutzte CC120/NoteOn-Neubelegung war als Lastreset
ungeeignet: eine lokale Engine-Gegenprobe zeigte nach erneuter Ein-Stimmen-
Belegung **zwei** nicht stumme Chip-Stimmen, obwohl nur ein Synth-Slot belegt
war. Der Chip lässt nach ausgeschalteter Envelope-Engine vorhandene
Volumenziele bestehen. Normale NoteOffs mit ausgerendertem Release beseitigten
diesen Effekt bei 1/16/30 Stimmen nach 5.888 Frames. P132 verwendet deshalb vor
jeder Belegung dieselben **8.192 Release-/Drainframes**, außerhalb der normalen
Messpopulation und vollständig protokolliert. Ein eigener tatsächlicher
Windows-DLL-Kontrollfall zeichnet den CC120-Befund zusätzlich auf. Das ist ein
nachgewiesener Fehler der ursprünglichen Testvorbereitung, noch kein Nachweis
der Ursache der früheren Audio-Deadlineüberschreitungen. Der CC120-Produktcode
bleibt unverändert; dieser Produktbefund wird separat dokumentiert.

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
  und Bibliotheksanteile können darin verbleiben. In einer VM kann auch der
  Hypervisor eine vCPU unterbrechen, ohne dass Windows einen CSwitch sieht.
  Sampling zeigt Hotspots,
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
- Der Laborhost verwendet normale Threadpriorität und kein MMCSS/ASIO. Es gibt
  keine Prioritäts-/Affinity- oder CPU-Frequenzänderung zum Erzwingen grüner
  Ergebnisse. Ein echter DAW-Audiothread, dessen Treiber und die private
  Original-ROM-/SF2-Last müssen gesondert auf dem Zielrechner geprüft werden.
- Im Stresshost werden die GUI-Parameter über die echte Audio-Parameter-
  Schnittstelle automatisiert. Die drei realen EditorHost-Fenstertests laufen
  separat. Gleichzeitiges Win32-Painting und Browserbedienung desselben
  Plugins in einer echten DAW sind damit nicht abgenommen.

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
Die abgeschlossenen Ergebnisse sind unten einzeln belegt. Ein grüner
Workflow bedeutet keine Echtzeitfreigabe.

Reproduktion in einer administrativen Windows-x64-Testsitzung mit dem gepinnten
Steinberg SDK unter `external/vst3sdk` (synthetische Fixtures werden automatisch
außerhalb des Checkouts erzeugt):

```powershell
$env:P132_BASELINE_DIR=Join-Path $env:TEMP 'p132-before'
gh run download 42208362856 -n P132-Windows-1-Raw-ETW-Evidence -D $env:P132_BASELINE_DIR
cmake -S . -B build-p132 -A x64 -D125A_BUILD_VST3=ON -D125A_BUILD_ENGINE_PROBES=ON -D125A_BUILD_EDITORHOST_TEST=ON -D125A_P132_AUDIT=ON "-DP132_BASELINE_NORMAL=$env:P132_BASELINE_DIR/symbols/125A_AWE_Synthesizer.vst3"
cmake --build build-p132 --config Release --parallel 2
ctest --test-dir build-p132 -C Release --output-on-failure -V --timeout 180
./tests/p132/run.ps1 -Build build-p132 -Trial 1
# Zweite vollständige Serie auf einer NEUEN Runner-Zuteilung:
$env:P132_REVERSE='1'
./tests/p132/run.ps1 -Build build-p132 -Trial 2
```

Nach Ablauf der Artefaktaufbewahrung muss die Vorher-DLL aus dem exakt
gepinnten Stand 418cc6b neu gebaut oder aus einem eigenen geprüften Archiv
bereitgestellt werden. Ohne Vorher-DLL ist der Crossover-Nachweis NOT RUN.
Validator und GUI-Schritte sind in der Workflowdatei explizit aufgeführt.
Der Profilaufruf beendet nur selbst erfolgreich gestartete WPR-Sitzungen.
`qa/traced`, `qa/untraced` und `qa/memory` enthalten jeweils `callbacks.csv`,
`cases.csv`, Module und Auswertung; hinzu kommen `cpu.etl`, `heap.etl`,
TDH-Ereignistabellen, Maschinen-/Build-/Fixture-Hashes und die PDB/DLL-Dateien
für die Symbolauflösung in WPA. Die CI-Artefakte sind 14 Tage aufbewahrt.
Kompakte numerische Berichte werden zusätzlich mit SHA256-gesicherten
Check-Annotationen gespiegelt. Private ROM-/SF2-Dateien werden weder archiviert
noch für diese öffentlichen CI-Läufe verwendet.

## Quellcodeprüfung des Echtzeitpfads

`Processor::process()` pinnt die Engine über `RealtimeEngineExchange::Guard`.
Die Registrierung und Referenzzähler verwenden atomare fetch_add/fetch_sub;
der Guard-Destruktor zerstört keine Engine. Veröffentlichung, Collector,
Mutex/CV und Freigaben liegen auf Control-/Collector-Threads. Das Audio-Gate
von `RealtimeStateVersion::Writer` versucht genau einen strong-CAS; bei einem
Control-Writer wird die Audio-Transaktion abgelehnt und ein vorhandener Intent
später erneut angewandt. Der yield/CAS-Wartekreis gehört zum Control-Pfad.
Das belegt die Struktur, **keine obere Latenzgrenze** für Cache-Kohärenz,
Atomics, Page-Faults oder Betriebssystemunterbrechungen.

`scratch_` und 1.024 Parametercursor werden vor dem Prozessaufruf bereitgestellt.
Ereignisse und Parameterpunkte werden im Audiothread zusammengeführt; eine
bewegte Pitchkurve auf einem klingenden Kanal kann bewusst einzelbildweises
Rendern und IP-Registerschreiben auslösen. NoteOn, MIDI-Controller, Pan-Glides
und das Wiederherstellen gehaltener Noten nach Engineveröffentlichung können
zusätzliche Arbeit innerhalb eines Callbacks verursachen. Die begrenzten
Stimmenzahlen ersetzen daher keinen Test der dichten Automation.

Der Adapter hat einen 980-Chipframe-FIFO. `FlushBlock()` verarbeitet am Rand
verbliebene Registerschreibvorgänge und Chipframes; PortRead kann bereits vorher
bis zur aktuellen Position rechnen. P132 protokolliert seine unverändert
gelesene Phase und Chipposition. Ein Phasenübertritt ist zunächst nur ein
Quellcode-Merkmal; erst zeitgleiche Messdaten dürfen ihn mit einem Ausreißer
verbinden. Die inzwischen tatsächlich gemessene Korrelation wird durch einen
Vorher-/Nachher-Eingriff überprüft; Chorusformeln werden dabei nicht geändert.

Die Labor-Host-Vorbereitung (Event-/Parameterlisten, PCM-Hash, CSV und Pacing)
liegt außerhalb der process()-Zeitklammer. Dennoch beeinflusst sie den
Cachezustand und das Scheduling. Ebenso sind die synthetischen, geloopten
Einzelregionen kein vollständiges Orakel für jeden autorisierten SF2-Layerstack
oder das proprietäre Original-ROM. Öffentliche Tests enthalten nur neu erzeugte
synthetische Assets; das separate Plugin-Test-Lab bleibt unverändert.

## Reproduzierter Produktbefund P132-F01: 980-Frame-Arbeitsbursts

Unveränderte Produktionsbasis im Messcommit
`418cc6b580a8cb3fd770b33b3804e0626d3c08f8`:

| Windows-Zuteilung | Workflow | CTest | Validator | GUI | Prozess-Deadlinefehler, ETW / ohne ETW |
| --- | --- | --- | --- | --- | --- |
| A, Intel Xeon Platinum 8370C, 4 vCPU | [42208362856](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42208362856) | 43/43 | 47/47 | 3/3 | 591 / 243 von jeweils 43.200 |
| B, AMD EPYC 9V74, 4 vCPU | [42208362915](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42208362915) | 43/43 | 47/47 | 3/3 | 1.311 / 1.269 von jeweils 43.200 |

Beide Windows-2022-VMs: 2 Kerne / 4 logische Prozessoren; Angaben zu GHz aus
Win32_Processor sind **keine** gemessene dynamische CPU-Frequenz. Alle 172.800
Messcallbacks bleiben in den [vollständigen Zellstatistiken](evidence/p132/before/all-cases.csv)
und [Zuteilung A](evidence/p132/before/windows-1-summary.json) /
[Zuteilung B](evidence/p132/before/windows-2-summary.json) dokumentiert.
P50 und P99 benutzen nearest-rank-Ordnungsstatistiken; der P50 ist der untere
Median bei gerader Anzahl. Normale/DLL-Diagnose-Qualifikation benutzt das
arithmetische Mittel der zwei mittleren Werte. Einheit: Mikrosekunden.

Bei **128 Frames / 30 unverändert aktiven Stimmen / Render** beträgt das Budget
2.902,494 µs. Es gibt keine Stimmenunterfüllung und keinen Enginewechsel:

| Runner / Profil | P50 | P99 | Maximum | Überschreitungen / 3.000 |
| --- | ---: | ---: | ---: | ---: |
| A / CPU-ETW | 1.912,6 | 2.961,3 | 4.806,1 | 67 |
| A / ohne ETW | 1.881,3 | 2.879,5 | 3.585,0 | 20 |
| B / CPU-ETW | 1.837,3 | 3.065,1 | 3.764,7 | 393 |
| B / ohne ETW | 1.785,9 | 2.984,9 | 3.290,6 | 390 |

**Phasennachweis auf B:** Von 3.000 Rendercallbacks überschreiten 392 die
980-Frame-FIFO-Grenze. Mit CPU-ETW scheitern **392/392** dieser Grenzcallbacks;
P50 3.015,8 µs, geplante On-CPU-P50 ebenfalls 3.015,8 µs. Ohne Grenzübertritt:
P50 1.835,8 µs, 1/2.608 Fehler; dessen Walltime 3.764,7 µs enthält deutlich
weniger geplante On-CPU-Zeit. Ohne ETW scheitern 390/392 Grenzcallbacks,
**0/2.608** übrige. Die Median-Rohzyklen steigen mit ETW von 4.712.942 auf
7.727.590; ohne ETW von 4.616.430 auf 7.592.104. Das ist eine reproduzierbare
periodische Arbeitskonzentration, kein bloß vermuteter Windows-Kontextwechsel.
Andere Befunde dürfen nicht pauschal hierauf zurückgeführt werden.

Die beiden verlustfreien CPU-Traces enthalten zusammen 1.902 Überschreitungen:
1.894 mit geplanter On-CPU-Zeit über Budget, 6 mit allein ausreichender
Ready-Off-CPU-Unterbrechung und 2 mit anderweitig ausreichender Off-CPU-Zeit.
Alle gemessenen Zeilen haben vollständige rekonstruierte Zeitabdeckung;
Positivkontrollen zeigen jeweils rund 20 ms Sleep-Off-CPU und 20 ms Busy-On-CPU.
Diese Klassen sind absichtlich keine Behauptung, jede On-CPU-Spitze bestehe
vollständig aus DSP-Rechnung. Sampling ordnet unter anderem RenderVoice,
emu8k_update_chunk und Registerarbeit zu; nicht aufgelöste Bibliothekssamples
bleiben als solche erhalten. Reine Funktionszeit und Hypervisor-Effekte sind
hierdurch nicht vollständig getrennt.

## Korrektur und Gegenbeweis

Nur `src/engine/Emu8000Box.cpp` ändert sich in der Produktion. Der vorhandene
Chiprenderer wird zusätzlich bei 128, 256, …, 896 Chipframes bis zum aktuellen
Zeitpunkt vorgezogen; bei 980 Frames bleibt die bisherige FIFO-Veröffentlichung.
Registerschreibreihenfolge, deren originale Frameoffsets, Renderarithmetik,
Chorus/Reverb/EQ und FIFO-Latenz bleiben erhalten. Am FIFO-Ende verbleiben bis
zu 84 Frames; ein Hostcallback kann zwei Teilupdates enthalten. Keine neuen
Allokationen, Locks, Atomics, Warteoperationen oder GUI-Funktionen.

Die Arbeit wird verteilt, nicht durch eine spekulative Änderung des Klang-DSP
ersetzt. Deshalb kann der Median steigen, während der periodische Spitzenwert
sinkt. Vor dem Push geprüft:

- **34/34** vollständige native CTests bestanden (29,70 s).
- Vorher-/Nachher-PCM bei 44,1/48/96 kHz, 16 Stimmen, Cutoff/Q/Modulation und
  Voice-Stealing: **1.966.080 Byte bitgleich**, SHA256
  `3fd06d30470fdd4ee4841381d412a090e1b77dcc6dadce6ebd305afb8a93e756`.
- Derselbe Vergleich mit aktivierten Reverb-/Chorus-Sends: **1.966.080 Byte
  bitgleich**, SHA256 `e95a37329d613ec0cebe77cae92c3458831f75549eaf0fbad9ef13d0f0959f88`.

Die Windows-Nachprüfung ergänzt den tatsächlichen normalen Vorher-/Nachher-
DLL-Vergleich mit dichter MIDI-, Pitchbend-, Programm-/Bank-/Kanalprogramm-
und FX-Automation, CC120 sowie synchronen V10-Recalls. Beide DLLs müssen bei
jedem Block identische Float-PCM-Puffer und identische V10-Streams liefern.
Zusätzlich ABBA/BAAB-Vergleich alter und korrigierter Diagnose-DLL auf demselben
Runner: 128 Frames, 30 physisch kontrollierte Stimmen, Render/Save/Save+Recall,
zweimal 3.000 Blöcke je Zelle und DLL. Gleicher Host und gleiche musikalische
Last; nur die geladene DLL wechselt. Die Vollmatrix läuft weiterhin auf zwei
neuen Windows-Zuteilungen mit und ohne CPU-ETW, ergänzt um WPR-Heap und alle
Windows-Regressionen. Die abgeschlossenen Ergebnisse folgen unten.

## Recall-Lastbias und separater CC120-Befund

[Natürliche Recall-Kontrollen](evidence/p132/natural-recall-controls.json),
[Windows 42211942566](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42211942566),
Kontrollhost `5ac6f4407f97d08c826d4b0cc1c1b2e10b3c42e1`, **identische DLLs aus
418cc6b**, ohne Neubau der Produktion:

- In **allen zwölf** Kombinationen aus vier Puffergrößen und 1/16/30 Stimmen
  setzt ein normaler Save/Recall ohne neuere NoteOns die physische und gehaltene
  Stimmenzahl auf **0**. Diese vor dem Recall akzeptierten Noten fallen unter
  den bestehenden Recall-Intent-Cutoff. Solche Messungen taugen nicht als
  Rechenleistungsvergleich gegen gehaltene 30 Stimmen. P132 trennt deshalb
  sämtliche Übergangsblöcke und die lastgleiche Population, ohne Fehler aus
  der Gesamtpopulation zu entfernen.
- CC120 allein: 0 belegte Synth-Slots, aber **1 weiter nicht stumme Chip-Stimme**,
  Envelope-Engine aus; Float-PCM-Quadratsumme im späten Beobachtungsfenster
  **10,62501469347626**. Mit anschließender Ein-Stimmen-Neubelegung: 1 belegter
  Slot, **2** nicht stumme Chip-Stimmen, Quadratsumme **39,50683937035501**.
  Dieser eigenständige MIDI-/Chip-Stoppfehler bleibt offen. Er begründete die
  Korrektur der Labor-Lastvorbereitung; er erklärt nicht die reine Render-
  Phase mit 30 konstanten Stimmen. In P132 erfolgt deshalb keine zusätzliche
  unbelegte Änderung an KillVoice oder Chorus.

## Heap und verbleibende Abnahmegrenzen

Beide Vorher-WPR-Heap-Traces sind verlustfrei, mit korrekter QPC-Zeitbasis und
sämtlichen vier Kontrollgrößen **37/73/91/131 Byte**. In jeweils **1.440**
tatsächlichen, markierten Prozessaufrufen wurde **kein Heap-Ereignis** des
Audiothreads beobachtet. Das ergänzt die bestehende reine C++-new-Regression;
es ist kein unbegrenzter Nachweis für jede DLL-/SF2-/Hostkonfiguration.
Auch **beide Nachher-Traces** erkennen alle vier Positivkontrollen ohne
Datenverlust und enthalten **0** Heap-Ereignisse innerhalb zusammen **2.880**
markierter process()-Aufrufe. Die P130-C++-new-Regression besteht ebenfalls.
Heap-Tracing wurde vor dem uninstrumentierten Crossover erfolgreich deaktiviert
(`heapDisable=0`). Der Laborhost allokiert außerhalb der Prozesszeitklammer
zahlreiche SDK-Listen; der Nullbefund bezieht sich auf die Pluginaufrufe.

## Abgeschlossene Windows-Nachprüfung

**Getesteter Commit:** `45df2931e75e54b53e32352ffa45573943dca85d`.
Produktionskorrektur: `e1d2b64a06228496d53716e34b250902c4afd115`.
Nachfolgend änderte sich nur der Testumfang um aktive FX-Sends. Beide neuen
Runner sind Windows 2022 / AMD EPYC 7763, 2 Kerne / 4 logische Prozessoren.
Die Gegenprobe verwendet auf jeder dieser Maschinen zusätzlich die alte DLL.
Unterschiedliche VM-Zuteilungen werden nicht als identische Hardware behandelt.

| Nachher-Zuteilung | Actions | CTest | Validator | GUI | Vollmatrix-Überschreitungen ETW / ohne ETW |
| --- | --- | --- | --- | --- | --- |
| A | [42213516747 — SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42213516747) | **44/44** | **47/47** | **3/3** | **631 / 35**, je 43.200 Aufrufe |
| B | [42213516842 — SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42213516842) | **44/44** | **47/47** | **3/3** | **69 / 61**, je 43.200 Aufrufe |

Der zusätzliche CTest vergleicht die **tatsächliche normale Vorher-DLL** aus
418cc6b mit der normalen korrigierten VST3: **1.474.560 Stereo-Frames =
11.796.480 Float-PCM-Byte je Runner bitgleich**, plus identische V10-Streams
nach jedem der 3.072 verglichenen Blöcke. Alle 16 Kanalprogramm-IDs, Programm/
Bankwechsel, NoteOff/NoteOn, CC120, dichte Pitchkurven, Master-/GUI-Parameter,
aktive Chorus-/Reverb-Sends und synchrone Recalls sind enthalten. Die normale
und die separat gelinkte Diagnose-DLL bestehen zusätzlich ihren eigenen
zwölfzelligen PCM-/Stimmen-/V10-Vergleich. Das belegt die getesteten Stimuli,
keine unbegrenzte Gleichheit jedes denkbaren Projekts.

Alle [Nachher-Zellstatistiken einschließlich Crossover](evidence/p132/after/all-cases.csv),
[Nachher A](evidence/p132/after/windows-1-summary.json) und
[Nachher B](evidence/p132/after/windows-2-summary.json) sind dauerhaft abgelegt.
Dazu gehören Median/P99/Maximum, Fehlerzahlen, tatsächlich lastgleiche Anzahl,
Unterfüllung, Generationswechsel, ETW-Abdeckung und Rohzyklus-Phasenstatistiken.
Die vollständigen Callback-/ETW-Rohdaten liegen in den jeweiligen
`P132-Windows-1-Raw-ETW-Evidence` / `P132-Windows-2-Raw-ETW-Evidence`-Artefakten.

## Crossover: gleiche Maschine, gleicher Host, konstante 30 Stimmen

128 Frames / 44,1 kHz / Render, **sämtliche 3.000 Blöcke je Zeile mit 30 belegten
und nicht stummen Chip-Stimmen**, kein Enginewechsel, keine Unterfüllung.
A führt Vorher-1 → Nachher-1 → Nachher-2 → Vorher-2 aus, B die umgekehrte
BAAB-Reihenfolge. Zeiten in µs, Budget 2.902,494 µs:

| Runner | DLL / Wiederholung | P50 | P99 | Maximum | Deadlinefehler |
| --- | --- | ---: | ---: | ---: | ---: |
| A | Vorher-1 | 1.795,7 | 2.912,0 | 4.771,9 | 40 |
| A | Nachher-1 | 1.914,9 | 2.186,6 | 2.510,5 | 0 |
| A | Nachher-2 | 1.911,2 | 2.191,5 | 3.581,5 | 1 |
| A | Vorher-2 | 1.786,0 | 2.872,2 | 3.788,7 | 11 |
| B | Nachher-1 | 1.917,2 | 2.095,9 | 2.849,2 | 0 |
| B | Vorher-1 | 1.788,4 | 2.889,0 | 3.164,6 | 22 |
| B | Vorher-2 | 1.785,3 | 2.887,5 | 3.644,6 | 17 |
| B | Nachher-2 | 1.919,3 | 2.067,4 | 3.051,2 | 1 |

Damit **90/12.000 → 2/12.000** Überschreitungen im konstanten Rendervergleich.
Das ist ein Nachweis der Verbesserung auf denselben Maschinen, kein Null-
Fehler-Nachweis. Der höhere Median ist erwartbar: Die gleiche Rechenarbeit
wird auf zuvor günstigere Blöcke verteilt. Die alte 980-Grenzsignatur ist
abgeflacht. Beispielsweise haben auf B mit CPU-ETW die 392 korrigierten
Grenzblöcke im Save-Fall **0** Fehler (P99 2.235,1 µs), die übrigen 2.608 Blöcke
**2** Fehler (P99 2.150,2 µs). Die früheren Grenzbursts treten somit nicht
unverändert an derselben Phase auf.

Die vollständigen Crossover-Fälle bleiben erhalten:

| Lastfall, je 12.000 Aufrufe pro DLL | Vorher: alle / lastgleiche Fehler | Nachher: alle / lastgleiche Fehler |
| --- | ---: | ---: |
| Render | 90 / 90 | 2 / 2 |
| Save | 84 / 84 | 14 / 14 |
| Save+Recall | 599 / 387 | 138 / 131 |

Recall-Populationen haben unterschiedlich viele kalte Übergangsblöcke; die
Gesamtsummen dieser Zeile dürfen nicht als alleiniger CPU-Gewinnnachweis
benutzt werden. Der Renderfall benötigt diese Einschränkung nicht. Zusammen
wurden in Vorher-Vollmatrix, Nachher-Vollmatrix und Crossover **417.600**
gemessene reale Prozessaufrufe archiviert, zusätzlich alle markierten
Vorbereitungs-/Warmup-/Drain- und Heap-Kontrollaufrufe.

## Verbleibender Echtzeitbefund: FAIL

**796/172.800** Nachher-Vollmatrix-Aufrufe überschreiten ihr Budget. Auch in
lastgleichen Populationen verbleiben Fehler: A mit ETW **537**, ohne ETW **8**;
B mit ETW **36**, ohne ETW **29**. Die spätere korrigierte Crossover-Recall-
Wiederholung B/Nachher-2 hat **135/3.000** Überschreitungen, davon **128** bei
lastgleichen Stimmen, P99 **6.070,1 µs**, Maximum **16.276,0 µs**. Die erste
Nachher-Wiederholung desselben Runners hatte in diesem Fall **0/3.000**. Diese
schlechtere Serie wird ausdrücklich nicht weggelassen.

Weitere konkrete Gegenbeispiele zur Freigabe:

- Nachher A, ETW, 128 Frames / 30 Stimmen / Save: **410/3.000** Fehler,
  alle lastgleich; P99 **3.636,7 µs**, Maximum **6.968,1 µs**. Die Fehler liegen
  jetzt sowohl innerhalb als auch außerhalb der 980-Grenzpopulation.
- Nachher B, ETW, 1024 Frames / 30 Stimmen / dichte Automation: ein lastgleicher
  Callback **30.969,3 µs** bei **23.219,955 µs** Budget; rekonstruierte
  Windows-On-CPU-Zeit **30.961,6 µs**, keine ausreichende Ready-/Waiting-
  Unterbrechung. Das ist nicht als bloßer Windows-Kontextwechsel erklärbar.

Beide Nachher-CPU-Traces sind verlustfrei und für alle gemessenen Zeilen
abgedeckt. Von **700** dortigen Überschreitungen sind **9** durch ausreichend
Ready-Off-CPU erklärbar, **690** überschreiten bereits mit geplanter Windows-
On-CPU-Zeit das Budget, **1** hat anderweitig ausreichende Off-CPU-Zeit. Die
690 dürfen **nicht** automatisch als reine DSP-Zeit und ebenso wenig als
bewiesener Schedulerfehler bezeichnet werden. DPC/ISR, Betriebssystemarbeit,
VM-Stalls, Bibliotheks-/Cachekosten und verbleibende DSP-Arbeit sind nicht
vollständig getrennt. In den Crossover-Serien ohne ETW ist eine solche
kausale Einzelattribution ausdrücklich NOT RUN.

**P132-F01 ist gezielt korrigiert und seine Wirkung durch denselben Runner und
bitidentisches PCM belegt. Die vollständige Echtzeitabnahme bleibt FAIL.**
Weitere Änderungen wären ohne zusätzlichen Ursachenbeweis spekulativ und
wurden entsprechend dem Auftrag nicht vorgenommen. Insbesondere erfolgte
keine Änderung der Chorusformeln und kein Versuch, Restspitzen durch höhere
Prozesspriorität, andere Musiklast oder wegselektierte Fehler grün zu machen.

Offen für die weitere Abnahme: physischer Windows-Zielrechner mit echter
DAW/ASIO/MMCSS-Ausführung, autorisierter Original-ROM/SF2-Last und gleichzeitig
bedientem Editor; vollständige WPA-Stackauflösung auch der bisher unbekannten
Instruktionsadressen sowie DPC/ISR-/System-/gegebenenfalls Hypervisor-Nachweis
für die verbleibenden Fälle. WPA-GUI und Zielrechner-ASIO sind **NOT RUN**.
Der zusätzliche CC120-Stoppfehler und der unabhängige Hardware-Chorusvergleich
bleiben separate offene Punkte.

**Eindeutige Entscheidung: Echtzeit FAIL im geprüften Windows-Labor.**
Funktionsregressionen/PCM/Heap-Prüfung in den dokumentierten Fällen PASS;
Zielrechnernachweis NOT RUN. Keine GUI-/Releasefreigabe, kein Merge. Alle
Änderungen verbleiben auf `audit/p132-realtime`.

## Prüfstand und Commitzuordnung

| Rolle | Exakter Commit |
| --- | --- |
| Unveränderte Produktionsbasis | `c7d803c1b328166f6f5edcb770aa9c9f8b49ecda` |
| Vollständige Vorher-Messung / alte DLL | `418cc6b580a8cb3fd770b33b3804e0626d3c08f8` |
| Numerische Wiederherstellung / natürliche Recall-Kontrolle | `5ac6f4407f97d08c826d4b0cc1c1b2e10b3c42e1` |
| Einzige Produktionskorrektur (Adapter) | `e1d2b64a06228496d53716e34b250902c4afd115` |
| Vollständig Windows-geprüfter Nachher-Stand einschließlich aktiver FX | `45df2931e75e54b53e32352ffa45573943dca85d` |

P131-Referenz PR #70: `8fe01428741cb74070fe8b387e24b4b7e60613b5`, nicht gemergt.
Steinberg SDK: `3cdf9ca5d1f5b1b21e0a86832aa4abe55607bd96`, Tag
`v3.8.1_build_84`. Synthetische ROM SHA256:
`30e14955ebf1352266dc2ff8067e68104607e750abb9d3b36582b8af909fcb58`;
synthetische SF2 SHA256:
`0958ebcf11db2328d35ebbbb0da731b29af39af5016dd3ded29fec87a3a2a7c5`.
Dateien/Hashes der tatsächlichen DLLs, PDBs, Sourcekopien und Buildprotokolle
sind in den zugehörigen Rohartefakten enthalten. Die dauerhaft eingecheckten
numerischen Berichte enthalten ausschließlich Messdaten; [Herkunft und
SHA256-Nachweis](evidence/p132/README.md). Nach dem geprüften Nachher-Commit
werden nur Bericht, START-HERE und numerische Evidenz ergänzt.
