# P187 – korrigierter Windows-ETW-/ASIO-Test mit P186-Diagnose

## Warum dieses neue Paket nötig ist

Der Nutzer hat den ursprünglichen lokalen Ordner `P185-LOCAL-*` bereits
gelöscht. Die einzige verbliebene `P185-ACCEPTANCE.json` lautet
`ETW_NOT_AVAILABLE_OR_UNDECODABLE`, `INCONCLUSIVE` und
`physical_asio=NOT_RUN`. Der ursprüngliche Berichtsablauf hatte
`capture.json` und `asio.json` bereits gesehen, bevor der
Zusammenfassungsfehler ausgelöst wurde. `NOT_RUN` ist deshalb
nicht ausreichend, um eine tatsächlich unterbliebene
Referenz-ASIO-Ausführung zu belegen. Ohne die gelöschten Rohdaten
ist eine exakte nachträgliche Analyse unmöglich.

**P187 kombiniert die bereits im Windows-Test bestätigte
P186-Fehlerdiagnose mit einem neuen echten P185-ASIO-/ETW-Aufzeichnungslauf.**
Das universelle Test Lab liefert `P185-DIAGNOSTICS.ps1`
und die korrigierte `P185-RUN.ps1`; die eigentlichen
native ASIO-/ETW-Programme und der unabhängige MIDI-Sinus sind
gegenüber P185 identischer C++-Quellcode. Die AWE-DLL ist
die unveränderte ursprüngliche, geprüfte P178-DLL, läuft aber
**nicht** im neuen P187-Referenztest.

### Bedienung

1. Nur das **P187**-Windows-Artefakt aus dem erfolgreichen
   [P187-Actions-Lauf](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/workflows/p187-capture-windows.yml)
   vollständig in einen beschreibbaren Ordner entpacken.
2. DAW schließen, Audiointerface angeschlossen lassen,
   Monitor-/Kopfhörer-Lautstärke deutlich reduzieren.
3. `P187-ETW-ASIO.bat` **als Administrator** starten;
   den physisch registrierten ASIO-Treiber auswählen und
   nach eigener Zustimmung `START` eingeben.
4. Der Lauf verlangt keine Python-, ROM- oder SoundFont-Datei.
   Windows ETW muss durch das Betriebssystem erlaubt sein.
   Er führt genau **einen** echten Referenz-ASIO-Test
   bei **44.100 Hz / 512 Frames, 1.000 angeforderten Callbacks**
   aus (keinen AWE-/DAW-/Analogausgangs-Fidelity-Test).
5. Nur die neu erzeugte Datei
   `P185-LOCAL-*/P185-ACCEPTANCE.json` hier bereitstellen.
   **Nicht** die ETL-Dateien, originalen ROMs/SF2 oder
   die privaten Rohdaten hochladen; es gibt keinen automatischen Upload.

**Optionaler reiner Integritätstest:**
`P187-ETW-ASIO.bat -CheckOnly` (kein Audio, keine Aufzeichnung).

### Worin sich P187 von dem defekten P185-Bericht unterscheidet

Der Bericht enthält auch bei fehlender ETW-Korrelation die numerische
`diagnostic_summary` mit `events`, `cswitches`, `decode_errors`,
ETW-Session-Start-/Stop-/Open-/Process-Status, Verlust-/Frequenz-/Clockwerten,
Prozess-/Exit-Status und bis zu 32 Provider-GUIDs mit Aktivierungscodes.
Die Fehler werden getrennt als
`ETW_DECODE_ERRORS`, `ETW_ZERO_CONTEXT_SWITCHES`,
`ETW_MARKER_ENABLE_FAILED` usw. ausgegeben.

Ein lediglich gestarteter ASIO-Prozess bleibt
`REFERENCE_ATTEMPTED_UNVERIFIED`.
Nur nach validierten Nonce-/PID-/SHA-/Treiber- und tatsächlichen
Callback-Zahlen wird `REFERENCE_OBSERVED_BUT_ETW_INCONCLUSIVE`
ausgewiesen; nur nach vollständigen zusätzlichen QPC-/ETW-Prüfungen
`OBSERVED_REFERENCE_ONLY`. Eine abgebrochene Ausführung
oder null Kontextwechsel sind niemals ein Audio-/Scheduler-PASS.
Das ursprüngliche harte gesamte 2×Buffer-Startabstands-Gate
wird weder gelockert noch durch eine Warmup-Ausnahme ersetzt.

### Technischer Nachweis vor einem neuen Besitzerlauf

Das neue Paket verwendet den vollständigen P186-Test-Lab-Quellstand
`dfcb4527f1f46904c73c5f7f113b81c9c41ef70a`, dessen
**42 unabhängige Windows-Berichts-Gegenproben** bereits im
[Lab-Windows-Lauf](https://github.com/challanger2000/125A-Plugin-Test-Lab/actions/runs/42537198373)
bestanden haben, plus die P185-Nativ-ETW- und VST3-Lebenszyklus-Kontrollen.
Das AWE-Paket baut alle nativen EXE/DLL erneut und testet
die unveränderte Original-AWE-DLL-Provenienz, vorhandene AWE-Regression,
P185-Gegenproben **und** P186-Gegenproben unter Windows.
Ein erfolgreich erzeugtes **tatsächlich wieder heruntergeladenes
GitHub-ZIP** muss über seine eigene `P187-ETW-ASIO.bat -CheckOnly`
ohne ASIO-Hardware starten und eine absichtliche Dateiveränderung
zurückweisen.

Die P187-BAT wird nicht zur Freigabe eines AWE-Releases verwendet.
ASIO-Hardwareursache bis zur echten Zielrechnerauswertung
`INCONCLUSIVE`, AWE-Echtzeitabnahme `NOT_RUN`,
**FULL AUDIT NOT COMPLETE / RELEASE NO-GO**.
Die Original-P184-Messmatrix und Produktfunktion bleiben unverändert.
