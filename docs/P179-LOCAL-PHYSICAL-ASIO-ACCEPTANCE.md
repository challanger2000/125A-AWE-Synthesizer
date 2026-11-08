# P179 — echte ASIO-Callbacks mit AWE-MIDI und Original-SF2

Dieses Paket ist ein **lokaler Windows-Hardwaretest**, kein Plugin-Release.
Der ASIO-Host verwendet die originale 125A-AWE-VST3-DLL aus dem vollständig
geprüften P178-Paket und den erweiterten nativen ASIO-Host des 125A Test Labs.

## So benutzt du es

1. Das GitHub-Artefakt `P179-AWE-PHYSICAL-ASIO-LOCAL-TEST` vollständig entpacken.
2. Die DAW und andere Programme, die den ausgewählten USB-ASIO-Treiber
   exklusiv verwenden, vorher beenden. Der zuletzt tatsächlich verwendete
   Treiber war **Yamaha Steinberg USB ASIO**, nicht Audient.
3. Monitore/Kopfhörer leise stellen. Das Testsignal ist auf -20 dBFS begrenzt.
4. `P179-ASIO-TEST.bat` doppelklicken.
   Das aktualisierte Paket fragt **vor dem Streaming** die ASIO-Fähigkeiten
   direkt beim installierten Gerät ab (`IASIO::getBufferSize`,
   `IASIO::canSampleRate`). Die unterstützte Puffergröße wird gewählt,
   nicht mehr pauschal 256 Samples; möglich sind 64 bis 4.096 Frames.
   Nicht unterstützte Größen oder Sampleraten führen zu NO-GO statt PASS.
5. Lokale Dateipfade zur Original-ROM und zu einer bereits in P178
   bestandenen SF2-Datei eingeben, z. B. `Synth 512 Bank.sf2`.
6. Den tatsächlichen Audiointerface-ASIO-Treiber aus der Liste wählen,
   falls nicht genau ein geeigneter Treiber erkannt wird. Im letzten
   Testprotokoll stand **Yamaha Steinberg USB ASIO** mit exakt 512 Frames.
7. Mit Enter den Test explizit starten.

Keine Installation, kein Python, keine VM, keine Änderungen an Treibern.
Die Original-ROM und SF2 werden ausschließlich lokal gelesen, niemals
kopiert, in GitHub hochgeladen oder in den Ergebnisordner geschrieben.

## Was der reale Test macht

- Lädt die exportierte P178-AWE-VST3-DLL über den ursprünglichen echten
  VST3-Host-Pfad und verwendet lokal nur für den Host gesetzte
  Umgebungsvariablen `AWE32_ROM_PATH` und `AWE32_SF2_PATH`.
- Öffnet den in der Windows-Registry eingetragenen ASIO-COM-Treiber
  mit echter Geräte-Initialisierung und realen Hardware-Callbacks.
- Fragt die tatsächlichen ASIO-Puffergrenzen, bevorzugte Größe und
  Granularität vom Gerät ab; verwendet eine nachgewiesen unterstützte
  Größe (64–4096 Frames) und prüft 44,1/48/96 kHz auf Geräteunterstützung.
- Überträgt 1.000+ tatsächliche ASIO-Callbacks an das VST3-`process()`.
- Sendet MIDI NoteOn/NoteOff auf Kanal 1 für Note 48 / Velocity 100
  aus dem echten ASIO-Callback, mit vorallokierter Eventliste.
- Erfasst die Roh-PCM-Erzeugung vor dem sicherheitsbegrenzten Ausgang,
  verlangt Nonzero-Audio und Null ASIO-Deadlineverletzungen, XRUNs
  und fehlgeschlagene Audio-`process()`-Aufrufe.
- Belegt Plugin/Host-SHA256, Treibername, CLSID, einmaligen Session-Nonce,
  Rate, Buffer, Callbackanzahl und MIDI-Klang in zwei nativen JSON-Dateien.
- Ein unabhängiges Windows-PowerShell-Skript verifiziert beide Nachweise
  nochmals und schreibt nur lokale Text-/JSON-Ergebnisse in einen neuen
  Ordner `P179-LOCAL-RESULT-*`.

**Wichtig:** Dieser Test darf fehlschlagen, wenn der Treiber exklusiv belegt
ist, eine Rate/Blockgröße nicht unterstützt oder Windows einen echten
Deadline-Ausreißer meldet. Solche Situationen dürfen nicht in PASS
umetikettiert werden. Die Cloud-CI hat kein physisches Audient-Gerät,
daher kann sie nur Build, Formatkonverter und Fehlkonfigurationen testen.

## Fehlerfall aus dem Original-P179-Lokaltest

Der reale Windows-Lokaltest meldete
`Requested ASIO buffer size not supported by physical driver` bei der
früheren festen 256-Frame-Konfiguration. Daraus folgt **kein** DSP-FAIL;
ASIO-MIDI-Audio und Hardware wurden damals nicht ausgeführt. P101 behebt
nur die starre Auswahl, indem die tatsächlichen Gerätedaten ermittelt
werden. Noch immer ist ein erfolgreicher Hardware-Lauf erforderlich.

## Fehlerdiagnose nach dem zweiten echten Windows-Lauf

P179 erkannte beim zuletzt verwendeten **Yamaha Steinberg USB ASIO** die
tatsächlich zulässigen **512 Frames bei 44.100 Hz**. Das war korrekt;
der Test scheiterte anschließend jedoch an der aggregierten Meldung
`Physical ASIO real callback timing or DSP errors observed`.
Es ist **nicht bekannt**, ob eine DSP-Fehlverarbeitung, ein
ASIO-Overload/Resync, eine Aussetzer-Meldung, die Deadline-Uhr oder
eine unerwartete Sampleratenänderung beteiligt war. Ohne die rohen
Zähler darf keine Ursache behauptet werden.

**Die korrigierte P102-Diagnose** erstellt nach dem echten Driver-Stop
`ASIO-CALLBACK-DIAGNOSTICS.json` mit separaten, sessiongebundenen
Zählern (Audio, MIDI, ASIO, Latenz, mögliche Fehlerarten). Auch wenn
die volle Audioabnahme fehlschlägt, schreibt die `.bat` die überprüften
Zähler zusätzlich in `P179-ACCEPTANCE.json`.
Dieses neue Diagnosefile trägt ausdrücklich
`DIAGNOSTIC_ONLY_NOT_HARDWARE_PASS` und niemals eine
Release-/Hardware-Freigabe. Bei fehlendem ASIO-Gerät gibt es
**keinen** vorgetäuschten Diagnose- oder PASS-Nachweis.

Für die Nachanalyse genügt bevorzugt die neue `P179-ACCEPTANCE.json`;
alternativ kann `ASIO-CALLBACK-DIAGNOSTICS.json` mitgeschickt werden.
Private ROM- oder SoundFont-Dateien bleiben auf dem lokalen PC.

## P180 – Auswertung der dritten echten ASIO-Sitzung

Der reale P102-Diagnosebericht der nächsten Benutzersitzung enthält:

- **Yamaha Steinberg USB ASIO**, 44.100 Hz, 512 Frames.
- 1.000 angeforderte / 1.000 gelieferte ASIO-Callbacks.
- 1.000 erfolgreich ausgeführte VST3-Prozessor-Callbacks, 0 DSP-Fehler.
- 12 NoteOns / 12 NoteOffs; 1.019.251 nichtstille PCM-Samples.
- 0 ASIO-XRUN/Overload/Resync-Meldungen, 0 ungültige PCM-Samples.
- **1 Verletzung des Callback-Abstands:** maximal 62,6362 ms.
- Maximale Callback-Laufzeit 5,7598 ms, unter dem Blockbudget
  von 512 / 44100 = 11,60998 ms. Ausführungs-Deadlineverletzungen 0.

**Fazit:** Tatsächliche VST3-Audioberechnung und MIDI-Ansteuerung waren
innerhalb der 1.000 verifizierten Blöcke erfolgreich. Der strenge
ASIO-Abnahme-Gate bleibt jedoch wegen des einzigen langen
**Abstands zwischen** zwei Callbacks **NO-GO**. Es ist nicht nachgewiesen,
ob die Verzögerung durch Windows Scheduling, Gerät/Treiber, USB oder
andere Umstände ausgelöst wurde. Es ist weder ein nachgewiesener
AWE-DSP-Fehler noch eine vollständige ASIO-PASS-Bescheinigung.

Der gleichzeitig hochgeladene `P179-ACCEPTANCE.json` enthielt
`diagnostics_verified=false` und die reine native `[P102 DIAGNOSTIC
ONLY]`-Zeile als PowerShell-Fehler. Ursache im neu hinzugefügten Launcher:
Windows PowerShell 5.1 interpretiert auf `2>&1` umgeleitete native
Standardfehlerausgaben unter `$ErrorActionPreference='Stop'` als
abbruchauslösende `NativeCommandError`-Records. Dadurch wurde die
anschließende Überprüfung einer tatsächlich vorhandenen
`ASIO-CALLBACK-DIAGNOSTICS.json` vorzeitig unterbrochen.

P180 führt die beiden nativen Aufrufe über einen getrennten Wrapper:
Dieser protokolliert die native Standard-/Fehlerausgabe vollständig,
wertet weiterhin den **unveränderten nativen Prozess-Exitcode** aus
und stellt die ursprüngliche PowerShell-Stop-Regel anschließend wieder
her. Ein Windows-PowerShell-**5.1-Laufzeittest** muss beweisen, dass
native stderr bei Exitcode 0 nicht fälschlich fehlschlägt und bei
Exitcode 7 keinesfalls als Erfolg gilt. Die eigentlichen ASIO-Gates
werden **nicht gelockert**; eine Diagnose allein bleibt
`DIAGNOSTIC_ONLY_NOT_HARDWARE_PASS`.
## P181 – gezielte zeitliche Einordnung des echten ASIO-Ausreißers

Der bisher letzte reale Hardware-Lauf (Yamaha Steinberg USB ASIO,
512 Frames / 44.100 Hz) ergab **1.000 von 1.000** erfolgreich
verarbeitete Blöcke, **0 DSP-Fehler**, **0 ASIO-XRUN-/Resync-Meldungen**,
12 MIDI-NoteOns und 12 NoteOffs, jedoch weiterhin **eine**
Überschreitung des zulässigen Abstands zwischen Callback-Starts
(maximal 58,8728 ms); maximale Callback-Verarbeitung 6,7364 ms
gegenüber einem Blockzeitraum von 11,61 ms.

Die neue P181-Zeitspur ist dafür gedacht, **die Position im Ablauf**
der Auffälligkeit zu bestimmen. Während der tatsächlichen ASIO-Sitzung
werden Callback-Index, Thread-ID, Buffer-Index, QPC-Zeitpunkte,
NoteOn/Off-Stand und etwaige Treibermeldungen in vorab angelegte
Speicherzellen geschrieben. Nach dem Treiber-Stop entsteht
`ASIO-CALLBACK-TIMING-TRACE.json` mit jeweils vier benachbarten
Callbacks vor und nach jeder Auffälligkeit (keine privaten Audiodaten).
Das lokale `P179-ACCEPTANCE.json` enthält nun zusätzlich
`timing_trace_verified`, `timing_trace_gaps` und die einzelnen
`timing_trace_events` mit den genauen Zeitpunkten – so genügt
normalerweise wieder **nur eine JSON-Datei** für die Auswertung.

Das ist keine unabhängige Windows-ETW-/Kernel-Scheduling-Aufzeichnung.
Ein Wechsel der Thread-ID oder ein zeitlicher Zusammenhang mit einem
MIDI-Ereignis erklärt allein noch nicht die Ursache. Keine Grenzwerte
werden gelockert und kein Hardware-PASS wird aus dem Diagnoseformat
abgeleitet. Dieser P181-Lauf ist **nicht** erforderlich, um die
bisherigen 1.000/1.000-Audioerfolge erneut zu beweisen, sondern nur
zur weiteren Ursachenanalyse des einen Timing-Ausreißers.
## Abgrenzungen

Das ist ein echter Hardware-ASIO-/MIDI-Test, jedoch **keine Aufnahme von
analogem oder S/PDIF-Hardware-Audio** und **kein Studio-One-DAW-Test**.
Der Host misst intern vom VST3 erzeugtes PCM, während das Gerät
den Callback auslöst; er misst weder Wandlung noch akustischen Ausgang.
Das Studio-One-Projekt speichern, erneut öffnen und live bearbeiten
ist eine separate, weiterhin ausstehende Pflichtprüfung.

Hardware-Klangtreue (EMU8000 original vs. 86Box), unabhängiger FULL AUDIT,
Release-Freigabe und geprüfte Original-AWE32-ROM-Echtheit bleiben offen.

## Nachvollziehbarkeit / Lizenz

- AWE P178 Produkt-DLL und Lokalkit stammen aus dem geprüften
  [Windows Run #42496568131](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42496568131),
  exakt `cff9d91cdec5aa2574d039b23660fae0589c6878`.
- Der unabhängige Test-Lab-ASIO-Host mit MIDI-Erweiterung und P101-Bufferabfrage wird öffentlich
  aus der festgelegten P100-Quellrevision gebaut.
- Die ASIO SDK-Sourcen werden nur zum Build aus
  `audiosdk/asio@496a0765b8bb9c26f764f22f9a9712a937177db2`
  verwendet. Beachte die mitgelieferte ASIO-SDK-Lizenz (GPLv3 oder
  erforderliche proprietäre Rechte). Nicht ohne Lizenzprüfung vertreiben.
- Kein Merge nach `main`, keine automatische Releasefreigabe.
