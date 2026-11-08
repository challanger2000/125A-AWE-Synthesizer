# P182 – unabhängiger physischer ASIO-A/B/A-Gegenversuch

**Ausgangspunkt:** Die echten P179/P180/P181-AWE-Messungen mit
`Yamaha Steinberg USB ASIO` und dem ASIO-Host des Test Labs ergaben
jeweils **1** zu langen Callback-Startabstand bei **1.000/1.000**
erfolgreichen VST3-Prozess-Aufrufen, 0 zu langen Prozess-Ausführungen
und 0 gemeldeten ASIO-XRUN-/Reset-/Resync-Ereignissen. Die P181-QPC-Spur
lokalisierte die Lücke beim **dritten** Callback: **64,4333 ms** Abstand
bei 512 Samples und 44,1 kHz. Der AWE-Prozessor brauchte dabei nur
4,3576 ms. Ein Start-/Geräte-/Scheduling-Effekt ist plausibel,
aber **unbewiesen**.

## Aufbau

- Exakt dieselbe Windows-x64-Maschine, derselbe ausgewählte registrierte
  physische ASIO-COM-Treiber mit **einer CLSID**, derselbe gepinnte
  Test-Lab-ASIO-Host, dieselben vom echten Gerät abgefragten
  Sampleraten-/Puffergrenzen, MIDI Note 48, 1000 echte Audio-Callbacks
  **je Session**, dieselbe -20-dBFS-Ausgangssicherheitsgrenze.
- **A: SOURCE_BUILT_MIDI_SINE** – unabhängig aus Quellcode gebautes
  minimalistisches VST3-Instrument, erzeugt nur dann einen 220-Hz-
  Sinus bei 0,05 Peak, wenn die realen NoteOn-/Off-Ereignisse eintreffen.
  Ohne NoteOn bleibt es stumm. Keine 86Box-/AWE-/ROM-/SF2-Engine.
- **B: REAL_AWE_VST3** – exakt SHA-256-verifizierte, zuvor mit Original-
  ROM/SF2 getestete P178 AWE-DLL, kein neues DSP-Binary.
- **A: dieselbe Referenz-VST3-DLL erneut** – als zeitliche Kontrollprobe.
- Das Paket erfragt Original-ROM und SF2 **ein einziges Mal**, ohne die
  Dateiinhalte zu kopieren, hochzuladen oder im Bericht abzulegen.
- Vor jeder Session erzeugt der Launcher einen eigenen Session-Nonce;
  jede Session initialisiert denselben echten IASIO-Treiber neu,
  sendet NoteOn/NoteOff, stoppt den Treiber und schreibt unabhängige
  P102-Diagnostik und P181-Zeitspur in drei getrennte Ordner.
- Zwischen den Sessions erfolgt eine kurze Treiber-Cooldown-Pause.
  Es wird **niemals** gleichzeitig in zwei ASIO-Instanzen gestreamt.

## Einmaliger Anwenderlauf (nur per BAT)

1. Das **neueste** aus erfolgreicher Windows-CI gebaute
   `P182-ASIO-REFERENCE-COMPARISON`-Paket vollständig entpacken.
2. DAW schließen und Monitore/Kopfhörer leise stellen.
3. `P182-ASIO-COMPARE.bat` doppelklicken.
4. Lokale ROM- und SF2-Pfade angeben. Richtigen USB-ASIO-Treiber
   auswählen – im bisherigen Befund `Yamaha Steinberg USB ASIO`.
5. Mit Enter **alle drei** realen, nacheinander laufenden
   ASIO-Tests ausdrücklich genehmigen.
6. Nur `P182-LOCAL-RESULT-*/P182-COMPARISON.json` hochladen.

**Keine Python-Installation, kein VM-/WLAN-/Treiber-Setup, kein DAW-Projekt.**
Das Referenz-VST3 gehört ausschließlich zum geprüften QA-Paket,
**nicht** in ein verkäufliches AWE-VST3-Release.

## Strenge Auswertung / Fehlermeldungen

- Jede Session verlangt 1000 tatsächliche IASIO-Callbacks und 1000
  erfolgreiche VST3-Process-Blöcke, tatsächliche MIDI NoteOn/Off,
  Nicht-Null-PCM, passende Session-Nonce, Treiber/CLSID und Host-/Modul-
  SHA256, vollständige QPC-Trace-Slots ohne Overflow.
- Das lokale Skript erhält den **unveränderten** nativen ASIO-Exitcode.
  Ein Realzeit-NO-GO wird nicht in PASS umgeschrieben. Seine
  unabhängige Diagnose bleibt dennoch zur Auswertung verfügbar.
  Positive Audio-/MIDI-Nachweise dürfen bei einem NO-GO nicht existieren.
- `P182-COMPARISON.json` enthält per Session den ursprünglichen
  strengen ASIO-Gate, Timestamp-Gaps (Index, Abstand, relative
  Startzeit, Prozessdauer, Thread-ID), MIDI- und PCM-Messwerte.
- Ein zeitlich ähnlicher Fehler im Referenzinstrument ist
  **Gegenevidenz gegen eine ausschließlich AWE-spezifische Ursache**.
  Bleibt nur AWE auffällig, wäre ein produktspezifischer
  Folgeversuch erforderlich – **kein Beweis einer DSP-Ursache**.
  Alle grünen Kontrollläufe wären nur auf diese drei Sessions begrenzt.
- Die kleinen 220-Hz-Sinusberechnungen sind **nicht**
  gleich schwer wie der AWE-EMU8000-Klangpfad. Die A/B/A-Reihenfolge
  reduziert, beseitigt aber nicht Einflüsse durch Windows/USB/
  Scheduling, Temperatur, Treiber-Neustart und Last.
- Es wird **kein** ursprüngliches Timing-Gate aufgeweicht,
  keine Start-Callbacks weggelassen, keine ASIO-Fehler verschluckt,
  keine unabhängige echte ETW- oder Hardware-PCM-Aufnahme ersetzt.
  Der Vergleich ist **diagnostisch**, meldet durchgehend
  `physical_asio_verified=false` und `release_approved=false`.
  DAW-Praxistest, Klang-Hardware-A/B, FULL AUDIT und Release bleiben offen.

## Grenzen des Cloud-Builds

CI baut das exakte AWE-VST3 und die physische ASIO-Host-Quelle
nicht neu, sondern nimmt die gepinnte Original-P178-DLL und baut
den gepinnten Test-Lab-Host **sowie das Referenzinstrument** aus
prüfbarem C++23/VST3-Quellcode. Ein öffentliches GitHub-Windows-
Runnergerät besitzt **keinen** echten Yamaha-ASIO-Interface-Treiber.
CI darf nur den Quellenbuild, Generator-Tests, Syntax/Vertrag und
negative fehlende Hardware testen. Ein A/B/A-Resultat ist erst nach
dem echten explizit freigegebenen lokalen .bat-Lauf gültig.
