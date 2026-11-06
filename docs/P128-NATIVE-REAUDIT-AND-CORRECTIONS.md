# P128: native Nachprüfung und Korrekturen vom 6. November 2026

**GUI NO-GO / RELEASE NO-GO. Keine vollständige unabhängige P128-Abnahme.**

Ausgangsstand ist `105f756f15253001ee1cd49a234c584ea60fca77` auf
`fix/p122-bank-dirty-audit`. Dessen Produktionsquellen und Tests sind identisch
mit dem verbindlichen Auditcommit `9080fe75e57dd11c8019898ff481ae11839fedc4`;
dazwischen wurden nur START-HERE und der Test-Lab-Workflow ergänzt.
Die nachstehende Ausgangsprüfung benutzte ein unverändertes externes Archiv
von `9080fe75`. Korrekturen und ihre Entwicklerregressionen sind davon getrennt.

## Tatsächlich reproduzierte Fehler im Ausgangscode

| ID | Reproduktion | Beobachtung | Ursache / Korrektur |
| --- | --- | --- | --- |
| R01 | Globalprogramm 9 erhält seinen Intentstempel; vor Erwerb des Audio-Writers schließt ein neuerer Recall (0,0) ab. | **FAIL:** V10 speichert (0,9), das PCM entspricht Programm 9. | `process::apply` benutzte nach Gate-Erwerb den alten Parameterwert. Jetzt werden globale und Kanalintents gemeinsam **innerhalb** des Writers erneut aufgelöst. |
| R02 | Gleiche Reihenfolge mit Kanal 4, Programm 9. | **FAIL:** Recall wird durch Kanalprogramm 9 / Override-Maske 8 überschrieben; falsches PCM. | Derselbe ungeschützte Übergang zwischen Intentannahme und Anwendung. Gemeinsame Auflösung berücksichtigt den aktuellen Recallboden und alle Kanalstempel. |
| R03 | Programm 9 wird bei besetztem Writer angenommen. Pending-Verarbeitung liest seinen Stempel; neuer Recall beendet sich vor Gate-Erwerb. | **FAIL:** der ältere Pending-Snapshot setzt erneut Programm 9. | Die Vorprüfung ist jetzt ausschließlich ein Pending-Hinweis; die tatsächliche Entscheidung erfolgt unter Writer-Ownership mit frischen Werten. |
| R04 | Recall publiziert eine neue Engine nach der Ereignis-Grenzprüfung, unmittelbar vor NoteOn auf der alten Engine. | **FAIL:** der Callback nimmt die Note an, aktuelle und folgende Blöcke bleiben stumm. | Die alte Engine verlor beim Austausch ihre nach Recallbeginn angenommenen Noten. Feste Snapshots der tatsächlich belegten Stimmen übertragen nur NoteOn-Identitäten **nach** dem Recallstempel. |
| R05 | Ein begonnener Audioblock hält eine alte Engine; ein Recall ohne Assets entfernt sie vor dem nächsten MIDI-Ereignis. | **FAIL:** SIGSEGV / Exit 139. | `canRender` blieb wahr, obwohl der Ereigniswechsel `synth_` auf nullptr setzte. Render prüft jetzt den aktuellen Pointer. |

Die Handoff-Snapshots lesen nur Audio-eigene Stimmen und werden vor Freigabe des
bisherigen Engine-Pins erstellt. Sie deduplizieren SF2-Layer anhand derselben
NoteOn-Identität, bewahren getrennte NoteOns derselben Taste und übernehmen
keine bereits freigegebenen oder gestohlenen Stimmen. Pedalstatus und
Deaktivierung werden explizit getestet. Stateformat V10 und Parameter-IDs
bleiben bestehen. Die Datenstruktur ist auf die physischen 32 Stimmen begrenzt;
keine zusätzliche Heap-Allokation, kein Audio-Mutex und keine Retry-Schleife.

## Echtzeitbefund und exakte Optimierung

Der Ausgangscode überschritt das Budget von 23,219955 ms bei 44,1 kHz / 1024
Samples erneut. Im ungepaceten Durchsatztest mit parallelen Saves wurden unter
anderem gemessen:

| Last | Callbacks | Wall p95 / p99 / Maximum (ms) | Thread-CPU-Maximum (ms) | Überschreitungen |
| --- | ---: | --- | ---: | ---: |
| 30 Stimmen | 501 | 17,5648 / 24,1755 / 24,3103 | 24,3090 | 13 |
| 16 Stimmen + 128 Bendpunkte | 501 | 11,9262 / 16,5348 / 29,7243 | 29,6953 | 1 |
| 1024 globale Programmpunkte | 501 | 10,9845 / 14,8061 / 25,8042 | 25,8022 | 1 |
| 30 Stimmen + Recall | 502 | 17,9661 / 25,4877 / 25,6142 | 25,6131 | 9 |

Dies sind Linux-VM-Messungen, keine Windows-/ASIO-Deadline-Abnahme.

Der Chamberlin-Filter berechnete `pow`, `sin` und `log2` für identische
Cutoff-/Q-/Modulationswerte bei jeder Stimme und jedem Sample erneut. Die
Korrektur speichert ausschließlich Koeffizienten für **exakt identische** drei
Eingaben pro Stimme. Bei Änderung einer Eingabe wird die ursprüngliche Formel
unverändert ausgeführt; Filterzustand und Signalrechnung werden nicht verändert.

`125A_p128_filter_cache_pcm` vergleicht den tatsächlichen PCM-Strom einer
gecachten und einer zwangsläufig ungecachten Engine bei 44,1 / 48 / 96 kHz,
unabhängig veränderten Cutoffs, allen Q-Werten, Modulation und Voice-Stealing.
Zusätzlich wurde derselbe Renderer gegen die unveränderte ursprüngliche
Engine gelinkt. Alle drei Ausgaben sind bytegleich. Negative Kontrollen mit
jeweils fehlendem Cutoff-, Q- oder Modulationsschlüssel erzeugen andere PCM-Daten
und werden erkannt. Das ist eine Rechenoptimierung, keine neue Filterabstimmung.

Ein zusätzlicher Vergleich im tatsächlichen nativen Processor-Pfad mit 16
Stimmen und konstantem Cutoff-/Resonanz-Overlay (je 500 Callbacks, ohne parallele
Builds) ergab ungecacht/gecacht CPU-p95 12,5219 / 11,3549 ms und CPU-p99
14,8182 / 12,4235 ms. Das belegt einen begrenzten Nutzen in dieser Konstellation,
keine allgemeine Deadline-Garantie.

**Echtzeit bleibt FAIL:** Im erneuten, mit 23,219955 ms gepaceten Save-/Recall-Lauf
hatten 30 Stimmen 5 Überschreitungen bei 500 Callbacks (max. 29,8490 ms);
30 Stimmen plus Recall hatten 25 bei 513 (max. 56,2413 ms). Dichte Bend-Automation
blieb ebenfalls betroffen. In sämtlichen neun Lastkonstellationen wurden im
markierten `process()`-Bereich 0 C/C++-Allokationsaufrufe und 0
`pthread_mutex_lock`-Aufrufe gezählt. Das sind instrumentierte lokale Messungen;
insbesondere ist damit kein Zielhost-Scheduler oder jede mögliche
Allokations-/Lock-API abgenommen.

ASan/UBSan/LeakSanitizer bestanden sechs ausgewählte Tests (Processor-Ordnung,
Engine-Entfernung, Note-Handoff, Engine-Exchange, Retirement, Filter-PCM).
Die aktualisierten unabhängigen PCM-Orakel wurden zusätzlich unter Sanitizern
wiederholt. LeakSanitizer benötigte Ausführung außerhalb des ptrace-Wrappers.
Sieben externe Processor-Mutationen und drei fehlende Filter-Cache-Schlüssel
wurden erkannt; falsches gespeichertes Programm und falsches Programm-PCM sind
getrennte Negativkontrollen.

## Messbare Testabdeckung und Grenzen

| Prüfung | Ausgangscode | korrigierte Arbeitskopie |
| --- | --- | --- |
| Native CTests ohne SDK | PASS, 27/27 | Im SDK-Build enthalten |
| Native CTests mit SDK / neuen Regressionen | neue Fehler oben reproduziert | PASS, 31/31; Processor-Ordnung 83/83 Einzelprüfungen |
| Kohärente V10-Roundtrips, vier Konstellationen à 30.000 | PASS, 120.000 | PASS, erneut 120.000 |
| Kanalprogramm/Recall mit zwei echten Threads und wechselnden 16 Kanälen | PASS, 30.000 | PASS, erneut 30.000 |
| Sofortiger Save bei verweigertem RT-Writer, inkl. erzwungenem Fallback | PASS in den gezielten Fällen | PASS in den gezielten Fällen |
| 500 Saves je neun Lastkonstellationen / frische inaktive Processor-Wiederherstellung | PASS, 4.500/4.500 | PASS, je 4.500/4.500 im Durchsatz- und im gepaceten Lauf |
| Unterscheidbare (0,0), (0,7), (0,9), (5,0), (5,7), (5,9) | PASS | PASS, außerdem gegen direkten Synth als unabhängiges PCM-Orakel |
| Original-Windows-DLL, Controller, echter Browser-Select und EditorHost | NOT RUN | NOT RUN |
| Original-ROM, autorisierte Referenz-SF2, Originalhardware, Studio One / ASIO / Offline-Export | NOT RUN | NOT RUN |

Ein frischer Processor wird im Save-Stresstest wirklich erzeugt, initialisiert,
mit dem vollständigen gespeicherten V10-Stream restauriert und erneut gespeichert.
Diese 4.500 Wiederherstellungen aktivieren nicht jeweils eine neue Audio-Engine.
Der Vergleich prüft V10-Inhalte und endgültige relevante Programmtupel; er ist
kein Beweis jeder denkbaren gleichzeitigen Ereignisordnung. Die deterministischen
Writer-/Recall-Fälle prüfen deshalb zusätzlich konkrete angenommene Änderungen
und tatsächliche erste und folgende PCM-Blöcke.

Die neuen Processor-Tests kompilieren den tatsächlichen Processor-Teil von
`Factory.cpp` gegen das gepinnte Steinberg-SDK
`3cdf9ca5d1f5b1b21e0a86832aa4abe55607bd96`. Ein Testgenerator entfernt ausschließlich
Controller/GUI/Factory-Entry, macht Felder für den Prüfstand sichtbar und fügt
Pause-Hooks hinzu. Dies ist kein nachgebautes Zustandsmodell, aber auch **kein
unabhängig gestartetes Windows-VST3-Binärartefakt**. Die normalen Windows-DLL-Tests
bleiben zusätzlich erforderlich. Die dauerhaften Testassets enthalten zusätzlich drei getrennte Programme in
Drumbank 128, damit auch MIDI-Kanal 10 ein unterscheidbares Programm-PCM-Orakel
hat. Die externen ursprünglichen Stress-/Timingläufe verwendeten die sechs
melodischen Presets; dort waren Drumprogramm-Klangunterschiede nicht abgedeckt.

Testquellen, externe Mutanten und Logs dürfen
nicht als Releasepaket ausgegeben werden.

## Chorus bleibt ein nachgewiesener Releaseblocker

Alle acht Presets wurden bei 44,1 / 48 / 96 kHz mit synthetischer SF2, CC93,
NoteOff und 60 Sekunden Tail wiederholt. Im Fenster 59–60 s waren je Rate nur
Preset 0 und 6 digital still: **6 PASS / 18 FAIL**. Unter anderem bleiben im
Standardpreset 2 −1 PCM-LSB und im Flanger 5 −7 PCM-LSB zurück. In diesen Fällen
werden die Silenceflags weiter korrekt als nicht still ausgegeben.
`kInfiniteTail` und `setProcessing(true/false)` bestehen die lokalen Prüfungen.
Hostseitiges Offline-/Idle-Verhalten ist NOT RUN.

Der Chorus-DSP wurde nicht verändert. Eine neue Rundung oder ein Noise-Gate wäre
ohne EMU8000-Referenzmessung keine bewiesene hardwaregetreue Korrektur.

## Wiederholung und noch erforderlicher Windows-Lauf

Native Prüfung (CMake >= 3.26, C/C++23, Python 3, SDK wie oben):

```sh
cmake -S . -B /tmp/awe-p128-build -DCMAKE_BUILD_TYPE=Release \
  -D125A_PROCESSOR_SDK_ROOT=/absolute/path/to/vst3sdk
cmake --build /tmp/awe-p128-build --parallel 4
ctest --test-dir /tmp/awe-p128-build --output-on-failure --timeout 120
```

Auf Windows werden die zusätzlichen Tests automatisch bei
`-D125A_BUILD_VST3=ON -D125A_BUILD_ENGINE_PROBES=ON` eingerichtet. Der vorhandene
Workflow `.github/workflows/p121-pitchbend-windows.yml` baut die echte VST3,
führt CTests, Validator und dreifache EditorHost-Smokes aus. **Dieser Lauf muss
für den korrigierten Quellstand neu erfolgen.** Frühere grüne Läufe und der auf
den alten Build gepinnte Test-Lab-Workflow validieren diese Änderungen nicht.

Die lokale Maschine ist Linux; Zugriff auf die GitHub-Actions-API über `gh api`
wird von der Netzwerkpolicy abgewiesen. Die öffentliche Workflow-Webseite ist
lesbar. Der vorhandene Push-Workflow auf dem Entwicklungsbranch soll deshalb
den korrigierten Stand vollständig auf Windows prüfen; bis zum belegten Ergebnis
ist dieser neue Lauf NOT RUN. Keine GUI- oder Releasefreigabe wird daraus abgeleitet.
Am Repository `125A-Plugin-Test-Lab` wurde nichts verändert.

## Windows-CI: konkrete Fixture-Korrektur

Die Läufe #42161173900 (`9d97ed9`) und #42162133911 (`e0348fd`) bauten die
Windows-VST3 erfolgreich, scheiterten aber im Quellausschlusstest: Der
In-Checkout-CI-Build erzeugte seine synthetischen ROM-/SF2-Dateien innerhalb
`build-p121/`. Die neue öffentliche Fehlerannotation identifizierte genau
`125A_source_baseline_contract`, nicht einen DSP- oder PCM-Fehler.

Die Fixtures und PCM-Ausgaben liegen jetzt in einem vom jeweiligen
Buildverzeichnis abgeleiteten Unterverzeichnis des externen System-Tempordners.
Native Windows-Pfade werden für CMake normalisiert. Eine Konfiguration mit
Tempordner innerhalb des Checkouts wird ausdrücklich zurückgewiesen. Positiver
In-Source-Build-/Assettest und negative TMPDIR-Gegenprobe wurden lokal
reproduziert. Der strikte Quellausschlusstest wurde unverändert gelassen.
Die neuen P128-Testdateien sind außerdem in den bestehenden CI-Pfadfiltern
registriert. Der vollständige neue Windows-Lauf bleibt bis zu seinem Ergebnis
ausstehend.
