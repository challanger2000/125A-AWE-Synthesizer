# P185 – geprüfte Windows-ETW-/ASIO-Testumgebung

Auftrag: [Issue #91](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/91).
Stand: 8. November 2026. Das Windows-Softwarepaket ist geprüft. Der eigentliche
P185-Versuch am Zielinterface bleibt **NOT_RUN**, seine Ursache **INCONCLUSIVE**.
Die bestehende strenge P184-Gesamtabnahme bleibt **NO-GO**. Keine FULL-AUDIT-
oder Releasefreigabe, kein Merge.

## Download und Benutzung

[Ein geprüftes Windows-BAT-ZIP](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42531433260/artifacts/13637930245).
Artefakt `P185-AWE-ETW-ASIO-Windows-BAT`, ID `13637930245`, ZIP-SHA256
`01ef0e754bd1e3210448c5ec504a77f1391df69ccfbe202044fc8c0d70a3dbda`.
Die SHA256-Werte jedes Paketbestandteils stehen in `P185-PACKAGE.json`.

ZIP vollständig in einen beschreibbaren Ordner entpacken; DAW schließen und
Interface-Lautstärke stark absenken. `P185-ETW-ASIO.bat` als Administrator starten,
gegebenenfalls den physischen Treiber auswählen und ausdrücklich `START`
bestätigen. Danach erfolgt genau **eine** referenzbasierte ASIO-Aufzeichnung bei
44.100 Hz / 512 Samples / 1.000 angeforderten Callbacks. Keine ROM-/SF2-Abfrage,
keine Python-Installation, keine Treiberänderung. Ohne Zustimmung kein Audio.
`-CheckOnly` prüft das Paket ohne ASIO-Gerät und ohne Audio/ETW-Aufzeichnung.

Zur Rückgabe genügt `P185-LOCAL-.../P185-ACCEPTANCE.json`. Darin stehen
Quell-/Binäridentitäten, Nonce, tatsächliche ETW-Verlustzähler, Statistik und bis
zu 16 konkrete Lückenbeobachtungen einschließlich Ready-/Wartezeiten. Private
Dateipfade und Originalmedien werden nicht exportiert. Die vollständigen
Callback-/Lifecycle-Rohdaten, der lokale Aggregatbericht und zwei ETL-Dateien
bleiben getrennt lokal; es gibt keinen automatischen Upload.

## Quellen und unveränderte Vorgaben

| Bestandteil | Exakter Stand |
|---|---|
| Engineering-Regeln, vollständig gelesen | `bc26392ec7ea9f20f074bff84bbc47ab439d5fe0` |
| Übernommener AWE-P184-Stand | `3aaa2f736535dde3642ab7cea11d919059ff12bb` |
| Test-Lab-Ausgangspunkt, P183/P184-ASIO-Linie | `b2f06baf9a0734132228abc67f1da7576357f694` |
| Geprüfte universelle P185-Werkzeuge | `59762ae67a5878f4bade2e000672497acde4f763` |
| Geprüfter AWE-Paket-/Workflow-Code | `22d08278a20d9989e71393944bfbc31d640bf231` |
| Vollständiger AWE-Regressionslauf | `37e6294672b13ae7064fb8f4f79633aec8cfffb3` |
| Unverändert übernommene P178-AWE-DLL | `cff9d91cdec5aa2574d039b23660fae0589c6878`, Originalartefakt aus Run `42496568131` |
| ASIO SDK | `496a0765b8bb9c26f764f22f9a9712a937177db2` |
| VST3 SDK | `3cdf9ca5d1f5b1b21e0a86832aa4abe55607bd96` |

Branches: AWE `qa/p185-independent-etw-asio`, Test Lab
`feature/p185-independent-etw-asio`. Dokumentationscommits nach diesen geprüften
Quellen verändern die Binärdateien nicht. `main` wurde nicht geändert.

AWE `src/` und CMake sind gegenüber P184 unverändert. P179–P184-Nachweise wurden
nicht überschrieben. Klangkern, Filter, ROM/SF2-Verhalten, 28-MiB-Sample-RAM-Grenze,
GUI, gesamter 2×Buffer-Spacing-Grenzwert und XRUN-/DSP-Fehlergates bleiben erhalten.
Die Paket-DLL wurde gegen die ursprüngliche P178-Provenienz und SHA256 geprüft
und nach dem Packen nochmals byteidentisch bestätigt. Keine ROM/SF2 oder fremden
Installer werden mitgeliefert. Die P184-A/B/A-Hardwaremessung wurde nicht wiederholt.

## Implementierung und geprüfte Erkenntnisse

Die Implementierung liegt im universellen Test Lab. Zwei eigene native
Windows-ETW-Sitzungen erfassen Kernel-Scheduling/CSwitch/ReadyThread, DPC/ISR und
verfügbare Microsoft-USB-/Audio-Provider. Laufzeitfehler und Rechte werden wirklich
geprüft; ADK/WPR ist für diese Erfassung nicht nötig. Fremde Sitzungen werden weder
ersetzt noch beendet. Rohdaten werden erst nach Ende des Streams ausgewertet.

Zwei vom Audio-Thread getrennte Provider-Marker liegen innerhalb tatsächlicher
QPC-Vorher-/Nachher-Klammern. Frequenz und Clock-Typ beider ETL-Dateien, PID/TID,
Nonce, Quell- und Binär-SHA sowie Kernelabdeckung über den letzten Marker hinaus
müssen zusammenpassen. Verlust, fehlende Marker/Schema/Rechte oder uneindeutige
Zuordnung verhindern die Ursachenbewertung; es gibt keine synthetische Ersatzmessung.

Die bisherigen Start→Start-Abstände werden ausdrücklich von vorherigem Ende→Start,
Callback-Wandzeit, IASIO-Start/Stop und Aktivierungsgrenzen getrennt. Das historische
`lastEndNs` speichert tatsächlich den vorherigen **Start**; seine bisherige
Grenzwertberechnung bleibt unverändert. Der ASIO-Callback-Körper ist gegenüber der
Test-Lab-Basis bytegleich (SHA256
`a31e4c7ee22f9943c58e99db2bb0ca7f6a662cafa8a5d6545539450d4f6906fa`).
Kein zusätzlicher Audio-Heapzugriff, Lock, Logging oder ETW-Aufruf wurde eingeführt.
QPC-Einstieg nach den vorhandenen Eingangsatomics und Ende vor Trace-/Deadline-
Buchhaltung bleiben als Messgrenzen dokumentiert. Die gemessene Wandzeit bzw.
Scheduling-Obergrenze wird ausdrücklich nicht als isolierte DSP-CPU-Zeit bezeichnet.

Reproduzierte Werkzeugfehler wurden gezielt korrigiert: ungeeignete unittest-
Discovery für vorhandene CLI-Tests; erhaltene erwartete negative Native-Exitcodes;
PowerShell-5.1-JSON-Arrayzählung; fehlender expliziter WPR-Status im älteren
Regressionsbericht; möglicher Verlust benötigter Quelldateien beim Artefakt-Upload.
Die Gegenproben prüfen außerdem einen abgeschnittenen Kernelabschluss, manipulierte
Identitäten/Uhren/Verlustdaten und falsche Attribution. Nicht dokumentierte
Kernel-Opcodes bleiben unklassifiziert; ein ausgeführter nativer Negativtest
verhindert ihre falsche Kennzeichnung als DPC/ISR. Es wurde kein neuer AWE-DSP-
Defekt reproduziert und keine spekulative Klangkorrektur vorgenommen.

## Tatsächlich ausgeführte Windows-Nachweise

| Nachweis | Ergebnis und Actions |
|---|---|
| Alle AWE-CTests, reale exportierte DLL, PCM-/MIDI-/State-Gegenproben | **66/66 PASS**, [Run 42529874449](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42529874449) |
| Tatsächliche VST3-Modulvalidierung | **537/537 PASS**, derselbe Lauf |
| Reale EditorHost-Smokes / weitere GUI-Prüfschritte | **3/3 / 99 PASS**, derselbe Lauf |
| Universeller echter Test-Lab-Host: State/Recall/GUI/Isolation | **TECHNICAL_PASS**, derselbe Lauf; keine Produktfreigabe |
| Gesamter Test-Lab-Release-Build, 2 CTests, 67 vorhandene Python-Skripte plus echter HWND/BMP-Test | **PASS**, [Run 42531360274](https://github.com/challanger2000/125A-Plugin-Test-Lab/actions/runs/42531360274) |
| Tatsächliche native ETW/QPC-/CSwitch-/Thread-End-/Rechte-Gegenproben, echter Referenz-VST3-Lifecycle und kaputte Referenz | **PASS**, Test-Lab-Lauf und [AWE-Paketlauf 42531433260](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42531433260) |
| Unabhängige positive/adversariale Parserfälle | **36/36 PASS**, Windows PowerShell 5.1, beide Läufe; synthetische Fälle bleiben Hardware **NOT_RUN** |
| Entpacktes ZIP: echter BAT-Start aus Pfad mit Leerzeichen, Abbruchcode 2, Manipulation abgewiesen mit 3 | **PASS**, Paketlauf |
| Dasselbe tatsächlich hochgeladene Nutzerartefakt erneut heruntergeladen und über seine eigene BAT/hashgeprüft | **PASS**, Paketlauf; erforderliche versteckte Quelldateien bleiben erhalten |

Die numerische Legacy-Regressionszusammenfassung wurde aus den veröffentlichten
CI-Notices rekonstruiert und gegen SHA256
`5711cf4ac3d6fc6e5b082035151753fdc6717b451f3592157adb68b8232d61d0`
verifiziert. Ihre 14.400 Offline-Callbacks hatten in diesem Lauf 0 gemeldete
Überschreitungen. Das bleibt ein synthetischer Softwaretest auf geteiltem
Windows-Runner; Recall verändert dort die gehaltene Last. Es ist keine
Echtzeitfreigabe und keine neue reale ASIO-Messung.

## Beobachtet, Hypothese, Ursache und verbleibende Grenzen

**Beobachtet:** Die vorliegenden P184-Echtmessungen zeigen die frühe Lücke auch in
der Referenz. Neu nachgewiesen sind das funktionierende Windows-Erfassungs- und
Korrelationswerkzeug sowie die oben genannten Softwaretests. Eine ausschließlich
AWE-DSP-bedingte Erklärung ist damit weiterhin nicht gestützt.

**Hypothesen:** Scheduler-Ready-Verzögerung, Wartezustände, USB-/Treiberstart und
Hoststart bleiben mögliche Untersuchungsrichtungen. Berechnete Ready-/Warteintervalle
sind Beobachtungen. Zeitliche Nähe von USB-/DPC-Ereignissen beweist keine Ursache.

**Nachgewiesene Hardwareursache:** keine. Reale P185-Korrelation am Yamaha Steinberg
USB ASIO, proprietäre Treiberprovider-/Routineattribution, DAW und analoger Ausgang:
**NOT_RUN**. Ursachenentscheidung **INCONCLUSIVE**. Auch ein sauberer einzelner
Referenzlauf kann die AWE-Echtzeitfähigkeit nicht freigeben. Die ganze Laufzeit
inklusive Startup bleibt im bisherigen strengen Grenzwert, ohne Warmup-Ausnahme.

ETW kann das Startverhalten beeinflussen; optionale Provider und Rechte unterscheiden
sich nach Rechner. Raw-ETL kann private Systeminformationen enthalten und bleibt
lokal. Erzwungenes Beenden kann eine eigene ETW-Sitzung bis Abmeldung/Neustart
zurücklassen; normales Ende/abgefangenes Ctrl+C räumt eigene Sitzungen auf, und ein
Jobobjekt verhindert einen weiterlaufenden Audio-Kindprozess. Nicht-ASCII-Paketpfade
wurden nicht geprüft (**NOT_RUN**); geprüft sind Pfade mit Leerzeichen.

Reviewform: ausgeführter **SELF_CHALLENGE**, kein unabhängiger menschlicher
Releaseaudit. **FULL AUDIT NOT COMPLETE / RELEASE NO-GO.**

## Draft-PR-Sperre

Die Draft-PR-Erstellung wurde in beiden Repositories tatsächlich versucht und mit
`GitHub Actions is not permitted to create or approve pull requests` abgewiesen.
Der lokale GitHub-API-Zugriff ist zusätzlich mit `Forbidden` gesperrt. Die
Repository-Einstellung wurde nicht verändert; kein PR oder Merge wird behauptet.
[Konkreter vorbereiteter Review-Text](P185-DRAFT-PR.md) liegt vor.
