# P237 – hardwarekalibrierten 86Box-AWE32-Fork einbinden

## Implementierung

Der [86Box-AWE32-Fork von turican0](https://github.com/turican0/86Box-AWE32) ist die **primäre virtuelle AWE32-Klangreferenz**. Die vorhandenen Aufnahmen echter AWE32/AWE64-Hardware bleiben das unabhängige physische Klangorakel. Die bisherige Standard-86Box wird nur dort weiter für die Win95-Gast-Automation eingesetzt, wo der Fork die benötigten Automationsbefehle nicht unterstützt; ihre Audioausgabe ist kein Ersatz für die kalibrierte virtuelle Klangreferenz.

- Originalrelease: v6.0-AWE32-0.93 vom 30. September 2026, SHA-256
  cefd28b691bfe1149719d26f54729356af91f9c3f713cfa6bab747aa0fa16b09.
- Das Python-Werkzeug tools/p237_86box_awe32_fork.py mit Befehl install lädt genau dieses Windows-ZIP, verifiziert es vor dem Entpacken, prüft sichere Archivpfade und bestimmt die ausführbare Datei.
- capture startet den Fork auf einer ausdrücklich freigegebenen Wegwerf-Kopie einer vorhandenen VM mit EMU8K_TRACE und AWE32_WAV, ohne auf bestehende Originaldateien zu schreiben.
- audit verifiziert Portwrite-Trace, 44,1-kHz-Chiptakt und WAV-Format (Stereo, PCM16, 44,1 kHz), zählt PCM-Grenzwerte und verweigert einen positiven Befund bei fehlenden Daten.
- Die Windows-2022-CI prüft den echten Release-Download und alle lokalen Vertragstests. Sie führt kein Win95-Gastsystem und keine Hardwareklangabnahme aus.

## Referenzpriorität und Automationskompatibilität

Unsere vorhandene produktive Engine basiert bereits auf der an echter AWE32-Hardware kalibrierten AWE32Emu-Implementierung, die dieser Fork verwendet.

Der Fork basiert auf 86Box 6.0 und bietet in diesem Stand nicht die neueren Automatisierungsbefehle des bestehenden P48-/P230-Prüfpfads (automation und automation-hold). Ein ungeprüfter Austausch würde die vorhandenen Creative-MIDI-Tests unterbrechen. Daher kein Austausch des laufenden Testsystems und keine Änderung an src/engine.

## Direkter originaler Creative-Treiber-/125A-Vergleich

Ab P237 gehört die neue compare-Funktion im vorhandenen Werkzeug tools/p237_86box_awe32_fork.py zur verbindlichen virtuellen Abnahme. Sie verwendet die echten EMU8K_TRACE- und AWE32_WAV-Dateien des gepinnten Forks sowie die korrespondierenden 125A-Register- und WAV-Daten. Gleiche ROM-/SF2-Fingerprints, MIDI-Ereignisse, Effekte und Chipzustände werden durch eine private match.json erzwungen. Der echte P67-Nachweis des gestarteten Windows-95-/Creative-Treibers und die SHA-256-Prüfung der Fork-Aufnahmen sind Pflicht. Die P89-Registernormalisierung wird wiederverwendet.

Ergebnis: per Stimme/EMU8000-Register verglichene Schreibserien, RMS-Pegeldelta, Differenz-RMS, samplegenaue Audioabweichung und 10-ms-Hüllkurvenkorrelation. Ohne globale Pegelnormalisierung. Bei Registerabweichungen zuerst die Creative-Treiber-/SF2-/Bankübersetzung untersuchen; bei gleichen Registern und unterschiedlichem PCM auch ROM/RAM, globale INIT-/FX-Register und DSP gegen den Fork prüfen. Jede bestätigte Klangkorrektur anschließend gegen P236 und die echten AWE32/AWE64-Aufnahmen absichern.

Die bestehende P237-Windows-CI hat die Vergleichsfunktion bislang **nur mit synthetischen Positiv-/Negativfällen** geprüft. Sie startet keine Win95-/Creative-VM und liefert daher **noch keine tatsächlichen Originaltreiber-/125A-Klangergebnisse**. Grüne Unit-Tests sind keine Hardware-Freigabe.

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
- Originaltreiber-MIDI-Wiedergabe im Fork: durch P237-Windows-CI noch nicht nachgewiesen.
- 125A-VST3-Klangtreue gegenüber echter Hardware: weiterhin nicht nachgewiesen.

P237 ist Infrastruktur, keine Klangfreigabe. Der Entwickler arbeitet unabhängig davon an der bestehenden Cutoff-Differenz und Codex an SF2-Dämpfung/Clipping.
