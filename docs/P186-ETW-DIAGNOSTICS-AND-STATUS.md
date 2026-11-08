# P186 – präzise ETW-Diagnose und korrigierter Referenzstatus

Auftrag [#92](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/92).
Ausgangspunkt AWE `4d56729788bcf065fbae1c13f5b79b831601d492`, Test Lab
`1425a5d86aaf228f16e03de55df182f38d990c32`; unveränderter nativer Stand
`59762ae67a5878f4bade2e000672497acde4f763`. Dedizierte Branches:
AWE `qa/p186-etw-diagnostics`, Test Lab `fix/p186-etw-diagnostics`.
Engineering-Basis `bc26392ec7ea9f20f074bff84bbc47ab439d5fe0`, START/README,
Audit-Completeness-Vertrag, Projekt-START, P184/P185 und Issues 91/92 angewandt.
Keine Freigabe, kein Merge, keine neue Hardwaremessung.

## Tatsächliche Ausgangslage

Der Besitzer hat P185 lokal ausgeführt. Das in Issue #92 bestätigte alte Ergebnis
ist INCONCLUSIVE / ETW_NOT_AVAILABLE_OR_UNDECODABLE mit irreführendem
physical_asio=NOT_RUN und acht Null-Verlustzählern. Der ausgeführte Kontrollpfad
hatte bereits die Existenz von capture.json/asio.json sowie vorgelagerte
Identitätsprüfungen passiert. NOT_RUN beweist hier **nicht**, dass keine ASIO-
Callbacks stattgefunden hätten. Es ist ein reproduzierter Berichtsfehler.

Die eigentlichen Nutzerdateien capture.json und asio.json wurden bislang weder
hier noch in Issue #92 bereitgestellt. Die vorhandenen gleichnamigen Cloud-
Dateien sind ausschließlich gekennzeichnete synthetische P185-Testfixtures.
Daher sind tatsächlicher PID/Exit, Callbackzahl, decode_errors und cswitches des
Zielrechners **NOT VERIFIED / INPUTS NOT PROVIDED**. Die acht Null-Verlustzähler
belegen keine fehlerfreie Decodierung. Kein Windows-/USB-/Treiberverursacher und
keine Windows-11-Schemaabweichung werden behauptet.

## Umsetzung / Grenzen

Die gemeinsame Test-Lab-Auswertung trennt ETW_MARKER_ENABLE_FAILED,
ETW_DECODE_ERRORS und ETW_ZERO_CONTEXT_SWITCHES ohne Lockerung eines Gates.
Mehrere gleichzeitig fehlerhafte Bedingungen bleiben als Liste erhalten. Ein
begrenzter, pfadfreier Bericht enthält tatsächliche numerische Rohzähler,
Kernel/User-Start/Stop/Open/Process/Frequenz/Uhrtyp/Verluste sowie bis zu 32
Provider-GUID-/Enable-Ergebnisse. Private Providernamen und unbekannte Rohfelder
werden nicht übernommen. Fehlende Zahlen werden nicht durch Null ersetzt.

Versuch, validierte Callbackbeobachtung und vollständige ETW-Korrelation sind
getrennte Zustände. Ein gestarteter Prozess mit noch ungeprüften Daten bleibt
REFERENCE_ATTEMPTED_UNVERIFIED. Nach geprüfter Quell-/Binäridentität, Nonce,
PID/Treiber und tatsächlichen Callbackzeilen/-zählern ist trotz ETW-Fehlern
REFERENCE_OBSERVED_BUT_ETW_INCONCLUSIVE möglich. Erst alle bisherigen
Korrelationsgates erlauben OBSERVED_REFERENCE_ONLY; das ist keine Audio- oder
Echtzeitfreigabe. Teilweise Verarbeitung bleibt teilweise, nie pauschal 1000/1000.
AWE-Realtime bleibt NOT_RUN und release_approved=false. Strenges gesamtes
2×Buffer-Timing samt Startup, XRUN-/DSP-Gates und P184-Nachweise unverändert.

Der native Decoder und sämtliche AWE-Laufzeitquellen sind unverändert; CI prüft
das gegen die exakten Ausgangscommits. Eine Windows-11-Anpassung wird erst nach
Auswertung der vorhandenen Originalzähler untersucht. Es gibt keine spekulativen
Feldnamens-Fallbacks, keine unterdrückten Decoderfehler und keine neue Soundengine.

## Vorhandene Daten statt Wiederholungsmessung

Die neue P186-EXISTING-RUN.bat wertet ausschließlich einen bereits gespeicherten
P185-LOCAL- oder RAW-LOCAL-ONLY-Ordner aus. Keine Administratorrechte, keine
Python-/Treiberinstallation, keine neuen ASIO-/ETW-Prozesse und keine neue
Audioausgabe. Das Paket enthält im Hauptordner keine Audio-EXE und keinen
Hardware-Launcher. Originaldateien werden nur gelesen. Ergebnis ist ein neues
P186-ACCEPTANCE.json; keine Originalmedien oder ETLs werden angefordert/hochgeladen.

Verwendet werden die **historischen** Host-/Referenz-Hashes aus dem tatsächlich
heruntergeladenen und geprüften ursprünglichen P185-Artefakt, nicht aus einem
neuen Build und nicht aus ungeprüften Eingabebehauptungen. Damit kann der schon
vorhandene Zielrechnerlauf geprüft werden. Vorhandene lokale CSVs ermöglichen
zusätzlich die unveränderte bisherige Korrelation; die zwei JSONs genügen zur
Diagnose der zusammengefassten numerischen Fehlerbedingung. Ohne Originaldateien
kann diese konkrete Zielrechnerdiagnose hier nicht vorweggenommen werden.

## Nachweismatrix

| Anforderung | Gegenprobe / unabhängiges Ergebnis | Stand |
|---|---|---|
| Originaler falscher NOT_RUN-Status | Exakter P185-Quellstand mit gültiger Referenzfixture und Decoderfehler, danach korrigierte Auswertung | Lokal reproduziert, Windows pending |
| Getrennte Decoder-/CSwitch-/Marker-/Startfehler | Dekodierfehler mit/ohne CSwitch, beide Bedingungen, echte Rechte-Negativkontrolle und Parserfälle | Lokal geprüft, Windows pending |
| Wahrheitsgemäßer Referenzfortschritt | Fehlendes ASIO, kein Kindprozess, partielle/fehlgeschlagene Verarbeitung, PID/Nonce/SHA/Wertebereich | Lokal geprüft, Windows pending |
| Keine kaputte ETW-Spur als Schedulingbeweis | Verluste, Uhr-/CSV-/Counterfehler, widersprüchlicher erfolgreicher Exit | Lokal geprüft, Windows pending |
| Pfadfreie begrenzte Ausgabe | Private Pfade in Zusatz-/Provider-/Zahlfeldern, 100 Provider | Lokal geprüft, Windows pending |
| Echter ZIP/BAT-Einstieg | CheckOnly/Abbruch, Originaldatei-Hashes, präzise Fehlergrade und Manipulation | Lokaler PS-Einstieg, Windows pending |
| Historische Binärpins und realer Artefaktdownload | Original-P185-Manifest/Dateihashes, unveränderte Quellen, Zip/Service-Roundtrip | Pending |
| Echte Nutzer-Rohdaten / tatsächliche Windows-11-Ursache | capture.json + asio.json des bereits gelaufenen Versuchs | NOT PROVIDED / NOT VERIFIED |
| Neu injizierter physischer ASIO-Teilfehler / neue Zielrechnermessung | In Cloud ohne physisches Interface nicht ausgeführt | NOT_RUN |

Reviewform SELF_CHALLENGE. Windows-Builds, reale native/VST3-Kontrollen und
PowerShell-5.1-/BAT-Ergebnisse werden erst nach tatsächlicher Ausführung ergänzt.
Die unveränderte Produktbaseline besitzt die historischen P185-Nachweise:
66 CTests, 537 Modul-Validatorprüfungen, 3 GUI-Smokes/99 GUI-Schritte; diese werden
nicht als neue P186-Produktprüfung umetikettiert. P186 ändert nur Test-/Berichtscode.

**Ursache INCONCLUSIVE / Gesamtfreigabe NO-GO / FULL AUDIT NOT COMPLETE.**
