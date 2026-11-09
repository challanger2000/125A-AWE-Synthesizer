# P188 – ETW-Berechtigung vor ASIO automatisch pruefen

Der echte P187-Zielrechner-Test hat gezeigt: StartTrace(Kernel)=5
und StartTrace(User)=5, d. h. **Windows verweigert den ETW-Sitzungsstart**.
Kein ASIO-Prozess, keine echten Audio-Callbacks, keine Decoderfehler.
Daher war die vorherige P187-Audiomessung **NOT_RUN**.

P188 korrigiert ausschliesslich den Windows-Starter und die
fruehzeitige ETW-/Administrator-Pruefung. Die universellen Test-Lab-EXE,
ihr nativer ETW-Decoder, der unabhängige Referenz-VST3 und die
AWE-DLL sowie alle strengen ASIO- und Release-Grenzen bleiben unverändert.

## So wird P188 verwendet

1. Das geprüfte P188-Windows-Artefakt vollständig in einen **beschreibbaren**
   Ordner entpacken.
2. DAW schließen und Interface-/Monitorlautstaerke deutlich senken.
3. `P188-ETW-ASIO.bat` normal starten; wenn der aktuelle Prozess
   nicht erhoeht ist, **fordert Windows automatisch per UAC**
   Administratorrechte an. Benutzer kann den UAC-Dialog ablehnen:
   dann **kein** ETW und **kein** Audio. Es werden keine
   Konten-/Gruppen-/Registry-/Treiberrechte veraendert.
4. Vor jedem ASIO-Start prueft P188 mit einem tatsaechlichen
   **ETW-Eigendiagnoselauf ohne ASIO** die Kernel-/Provider-Startrechte,
   Marker, Kontextwechsel und Decoderfehler.
   `P188-PREFLIGHT-*/P188-PREFLIGHT.json` speichert den
   exakten Windows-Fehlercode und den Admin-Token-Status.
5. **Falls ETW wieder scheitert, wird kein Audio-Test gestartet.**
   Dann bitte **nur `P188-PREFLIGHT.json`** bereitstellen.
6. Nur bei erfolgreichem ETW-Selbsttest geht es mit dem bekannten,
   expliziten `START`-Dialog zum **einmaligen**
   44.1-kHz-/512-Sample-/1000-Callback-Referenz-ASIO-Test weiter.
   Danach **nur `P185-LOCAL-*/P185-ACCEPTANCE.json`** bereitstellen.
   ETL/ROM/SF2/Provider-Rohdaten bleiben lokal und werden niemals
   automatisch hochgeladen.

Kein Python, keine VM, keine Treiberinstallation.

**Optionale sichere Kontrollen:** `P188-ETW-ASIO.bat -CheckOnly`
prueft die Paket-Hashes ohne UAC und ohne ETW/Audio.
`P188-ETW-ASIO.bat -PreflightOnly` prueft die echten ETW-Rechte,
startet aber **kein** ASIO und erzeugt keinen Ton.

## Interpretation

- Windows-Fehler 5 bei `StartTraceW` heisst `ERROR_ACCESS_DENIED`.
  Microsoft dokumentiert Administratorrechte fuer Kernel-ETW.
  Bei einem bereits erhoehten Token und Fehler 5 ist die Ursache
  noch genauer zu untersuchen (z. B. Sicherheitsrichtlinien);
  P188 aendert keine Gruppenrichtlinie und umgeht keine Schutzfunktion.
- `ETW_PREFLIGHT_PASS` ist ausschliesslich die Bestätigung der
  ETW-Messbereitschaft. **Es ist kein ASIO-, AWE-Echtzeit-
  oder Release-PASS**.
- Die originale P187-/P186-ASIO-Auswertung mit differenzierten
  `ETW_DECODE_ERRORS`/`ETW_ZERO_CONTEXT_SWITCHES` und
  abgestuften Referenzstatus bleibt im integrierten Test Lab.
- Nach wie vor: keine Warmup-Ausnahme, unveraenderter
  2×Buffer-Startabstands-Grenzwert, AWE-Release `NO_GO`
  und Zielrechner-P188 `NOT_RUN` bis zum wirklich abgeschlossenen Lauf.

Die Windows-CI prueft zusaetzlich den nativen ETW-Selbsttest,
den P188-eigenen `-PreflightOnly`, `-CheckOnly`, `-Cancel`,
manipulierte Pakete und das tatsaechlich heruntergeladene
GitHub-ZIP mit BAT.
