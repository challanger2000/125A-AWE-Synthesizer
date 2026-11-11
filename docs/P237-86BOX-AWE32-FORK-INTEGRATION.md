# P237 – hardwarekalibrierten 86Box-AWE32-Fork einbinden

## Implementierung

Der [86Box-AWE32-Fork von turican0](https://github.com/turican0/86Box-AWE32) ist als zusätzlicher, SHA-256-geprüfter Windows-x64-Backend integriert. Er ergänzt die bereits bestehende automatisierte Win95-/Creative-Testumgebung, ersetzt sie aber nicht.

- Originalrelease: v6.0-AWE32-0.93 vom 30. September 2026, SHA-256
  cefd28b691bfe1149719d26f54729356af91f9c3f713cfa6bab747aa0fa16b09.
- Das Python-Werkzeug tools/p237_86box_awe32_fork.py mit Befehl install lädt genau dieses Windows-ZIP, verifiziert es vor dem Entpacken, prüft sichere Archivpfade und bestimmt die ausführbare Datei.
- capture startet den Fork auf einer ausdrücklich freigegebenen Wegwerf-Kopie einer vorhandenen VM mit EMU8K_TRACE und AWE32_WAV, ohne auf bestehende Originaldateien zu schreiben.
- audit verifiziert Portwrite-Trace, 44,1-kHz-Chiptakt und WAV-Format (Stereo, PCM16, 44,1 kHz), zählt PCM-Grenzwerte und verweigert einen positiven Befund bei fehlenden Daten.
- Die Windows-2022-CI prüft den echten Release-Download und alle lokalen Vertragstests. Sie führt kein Win95-Gastsystem und keine Hardwareklangabnahme aus.

## Warum zusätzlich und nicht als Ersatz?

Unsere vorhandene produktive Engine basiert bereits auf der an echter AWE32-Hardware kalibrierten AWE32Emu-Implementierung, die dieser Fork verwendet.

Der Fork basiert auf 86Box 6.0 und bietet in diesem Stand nicht die neueren Automatisierungsbefehle des bestehenden P48-/P230-Prüfpfads (automation und automation-hold). Ein ungeprüfter Austausch würde die vorhandenen Creative-MIDI-Tests unterbrechen. Daher kein Austausch des laufenden Testsystems und keine Änderung an src/engine.

## Private Verwendung durch den Entwickler/Test-Lab-Runner

Auf einem isolierten Windows-x64-Runner kann der Fork automatisch bereitgestellt werden:

~~~powershell
python tools/p237_86box_awe32_fork.py install --out C:\P237\fork
~~~

Die automatisierte Aufzeichnung auf einer Wegwerfkopie einer bereits eingerichteten Win95-/Creative-VM:

~~~powershell
python tools/p237_86box_awe32_fork.py capture --binary C:\P237\fork\86Box.exe --vm C:\P237\private-vm-copy --roms C:\P237\roms --out C:\P237\private-capture --duration-seconds 90 --disposable-vm-copy
~~~

Die Gastumgebung muss die interessierenden Original-Creative-MIDI-Ereignisse selbstständig ausführen. Ohne diese Ereignisse können die aufgezeichneten Portwrites lediglich vom Initialisieren stammen. Eine solche Aufzeichnung ist keine originale Creative-Note-On- oder Hardware-Klangabnahme.

Alle privaten VM-/ROM-/SF2-/MIDI-/WAV-Dateien bleiben außerhalb des öffentlichen Repositories und werden von der P237-CI weder abgerufen noch veröffentlicht. Der neue Fork bleibt ein emulierter Chip, keine zweite physische Soundkarte.

## Status

- Codeintegration: Installations-, Capture- und Analysewerkzeug, Offline-Tests und Windows-CI sind im AWE-Projekt enthalten.
- Reproduzierbarer Binärbezug: veröffentlichter Windows-Fork samt SHA-256 festgelegt.
- Originaltreiber-MIDI-Wiedergabe in diesem Fork: nicht nachgewiesen.
- 125A-VST3-Klangtreue gegenüber echter Hardware: weiterhin nicht nachgewiesen.

P237 ist Infrastruktur, keine Klangfreigabe. Der Entwickler arbeitet unabhängig davon an der bestehenden Cutoff-Differenz und Codex an SF2-Dämpfung/Clipping.
