# P179 — echte ASIO-Callbacks mit AWE-MIDI und Original-SF2

Dieses Paket ist ein **lokaler Windows-Hardwaretest**, kein Plugin-Release.
Der ASIO-Host verwendet die originale 125A-AWE-VST3-DLL aus dem vollständig
geprüften P178-Paket und den erweiterten nativen ASIO-Host des 125A Test Labs.

## So benutzt du es

1. Das GitHub-Artefakt `P179-AWE-PHYSICAL-ASIO-LOCAL-TEST` vollständig entpacken.
2. Studio One/Fender Studio Pro und andere Programme, die dein Audient
   iD14-ASIO-Gerät exklusiv verwenden, vorher beenden.
3. Monitore/Kopfhörer leise stellen. Das Testsignal ist auf -20 dBFS begrenzt.
4. `P179-ASIO-TEST.bat` doppelklicken.
5. Lokale Dateipfade zur Original-ROM und zu einer bereits in P178
   bestandenen SF2-Datei eingeben, z. B. `Synth 512 Bank.sf2`.
6. Der echte installierte Audient-ASIO-Treiber wird wenn eindeutig erkennbar
   automatisch gewählt; andernfalls einen ASIO-Treiber aus der Liste wählen.
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
- Testet zunächst 44.100 Hz mit 256 Frames pro ASIO-Callback.
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
- Der unabhängige Test-Lab-ASIO-Host mit MIDI-Erweiterung wird öffentlich
  aus der festgelegten P100-Quellrevision gebaut.
- Die ASIO SDK-Sourcen werden nur zum Build aus
  `audiosdk/asio@496a0765b8bb9c26f764f22f9a9712a937177db2`
  verwendet. Beachte die mitgelieferte ASIO-SDK-Lizenz (GPLv3 oder
  erforderliche proprietäre Rechte). Nicht ohne Lizenzprüfung vertreiben.
- Kein Merge nach `main`, keine automatische Releasefreigabe.
