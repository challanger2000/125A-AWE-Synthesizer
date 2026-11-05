# Future backlog: Extended AWE Sampler — NACH Abschluss des klassischen Emulators

**Entscheidung des Projektinhabers (2026-11-05):** Die folgenden Erweiterungen **unbedingt vormerken**, aber **nicht jetzt implementieren**. Zuerst den 125A AWE-Synthesizer in der bisherigen originalgetreuen Auslegung fertigstellen. Der laufende P124-/Codex-GO-Prozess hat Vorrang. Weder Source-Code noch bestehende Releaseziele noch die 28-MiB-Grenze im Originalmodus währenddessen eigenmächtig verändern.

## Verbindliche Arbeitsreihenfolge

1. **P124 und offenen unabhängigen Nachaudit abschließen**; schwere funktionale Befunde vollständig beseitigen und nachprüfen. GUI bleibt bis GO gesperrt.
2. **Originalgetreue AWE32/AWE64-Emulation vervollständigen**, insbesondere die noch ausstehenden originalen EMU8000-Effekte / DSP-Verarbeitung (Reverb, Chorus, EQ soweit technisch/historisch zutreffend), mit Referenz- und Regressionstests. Keine Ersatzwirkung als Hardwaretreue deklarieren.
3. **GUI gegebenenfalls fertigstellen** (nur nach unabhängigem GUI-GO) und klassische Version end-to-end in Windows-VST3/Ziel-DAW mit echten, autorisierten ROM/SBK/SF2-Assets abnehmen; Release-GO eigenständig beurteilen.
4. **Erst danach** gesonderte Spezifikation, Machbarkeitsnachweis und Entwicklung des hier beschriebenen **Extended AWE Sampler**. Keine Vermischung mit der aktuellen stabilen Basis.

## Spätere Funktionen — vorgemerkt, nicht umgesetzt

- **Direkter WAV-Import** eigener Samples, statt ausschließlich fertiger SF2/SBK-Bänke. Spielbares Instrument aus WAV erzeugen können (Root-Key, Tonumfang, Sample-Start/Ende, Loop-Start/Ende, Tuning, Pegel). Import/Analyse/Umwandlung außerhalb des Audiothreads; persistente Projekt-/Presetverwaltung.
- **Multisampling** (Key-Zones), **Velocity-Layer**, Loop-Bearbeitung und eigene Instrument-/Kit-Presets als ausbaufähige zweite Stufe. Ein einzelner WAV-Import soll keine ungewollte Bankkonvertierung voraussetzen.
- **Extended AWE-Speicherziel bis zu 1 GiB für Sample-Daten**, deutlich über den historischen 28 MiB. Dies ist ein **Forschungs- und Entwicklungsziel, keine zugesagte erreichbare Speicherkapazität**.
- Der **EMU8000-Klangpfad** (Filter, Hüllkurven, Pitch/Interpolation, Chorus/Reverb etc.) soll möglichst dem originalen 86Box/EMU8000-Kern entsprechen; die Ausweitung soll sich primär auf Sampleversorgung/Adressierung beziehen, nicht die Klangerzeugung durch einen generischen SF2-Player ersetzen.
- Zwei logisch getrennte Modi: **Classic/Original** mit ROM-Pflicht und 28 MiB Hardwarelimit; **Extended** mit WAV-/großen SoundFont-Instrumenten und erhöhter Kapazität. Classic muss bit- bzw. referenzstabil bleiben. Ob Extended ebenfalls Original-ROM benötigt, wird **erst im Design** entschieden, nicht jetzt.

## Sound-Blaster-Synthesizer: ROM, WAV und optional OPL3 (nur Extended-Konzept)

**Idee des Projektinhabers (2026-11-05), ausschließlich für die spätere Planung:**
Der 125A-Synthesizer soll nicht nur existierende SoundFonts originalgetreu abspielen, sondern perspektivisch eigene Instrumente aus dem **historischen AWE-Sample-ROM** erzeugen können. Im Extended-Modus sollen ROM-Samples und eigene **WAV-Samples in mehreren Layern** kombinierbar sein; als zusätzliche, unabhängig spielbare Klangquelle ist die **OPL3-FM-Synthese** interessant. Denkbar sind eine virtuelle Tastatur, Preset-/ROM-Sample-Browser, ein übersichtlicher Layer-Editor, Klangregler und speicherbare eigene Instrumente. Diese Ideen sind **keine aktuellen Implementierungsaufträge**; sie dürfen weder P124 noch das Classic-Release verzögern.

- **ROM:** Die bereits unterstützte GM-ROM-Bank (Benutzer stellt ROM und `SYNTHGM.SBK` selbst bereit) beschreibt 128 melodische Presets und ein Drumkit. Ein frei editierbarer ROM-Sample-Pool und das Speichern neu zusammengestellter Instrumente benötigen einen zusätzlichen Instrument-/Preset-Editor; dies ist **noch nicht umgesetzt**.
- **WAV und Layer:** Samples mit eigenen Key-/Velocity-Zonen, Tonhöhe, Filter/Hüllkurven und Pegel kombinieren; ROM+WAV-Hybrid-Presets ermöglichen. Ein EMU8000-Layer verbraucht mindestens eine der historisch begrenzten Stimmen; Voice-Stealing, Polyphonie und Ausklang müssen getestet werden.
- **OPL3:** FM-Klangerzeugung als separate Synthese-Engine mit eigenem Instrument-Editor erwägen. OPL3 und EMU8000 waren auf der Sound-Blaster-Hardware getrennte Klangerzeuger. Eine gemeinsame Effektkette oder das Routing von FM-Audio durch EMU8000-Effekte wäre eine **optionale moderne Erweiterung**, keine behauptete historische Originalfunktion.
- **Ist-Stand:** Der Quellbaum enthält bereits eigenständige OPL3-/Creative-CQM-Module und Regressionstests; im aktuellen VST3 ist **kein aktiver OPL3-Instrumentenmodus** freigegeben. Keine stille Aktivierung oder Übernahme alter Projektmodi ohne späteren Design-/Host-State-Audit.

### Externe OPL3-Referenzprojekte — für die spätere Untersuchung festhalten

1. **ADLplug-Next**, https://github.com/yumasansansan/ADLplug-Next — geprüfter Stand: Entwicklungsbuild **2.1.12** (Nightly vom 2026-10-03). FM-Instrumenten-Editor, Preset-/Bank-Verwaltung, MIDI-Bedienung und Klang-/Performance-Vergleich verschiedener OPL3-Kerne einschließlich des eigenen OPL3-Emulators; auch OPN2 als separate Referenz. Eignet sich für **Konzeptvergleich und unabhängige Audiotests**, nicht als unkritisch zu kopierende Implementierung.
2. **OPL3GM VSTi / `OPL3GM_X64.zip`**, https://github.com/datajake1999/OPL3GM_VSTi — geprüfter Release **1.4.1** (2024-08-30). Historische FM-MIDI-Instrumente und Treiber-Mappings für **Windows 9x Sound Blaster**, **Doom** und **Apogee**; gut für Wiedergabe-/Preset-/Bankvergleich mit unserem OPL3. Das Referenzplugin ist **VST2**, keine aktuelle Windows-VST3-Produktbasis.

**Lizenz- und Qualitätsgrenzen:** ADLplug-Next enthält GPL-3.0-or-later-lizenzierte Änderungen; Lizenztexte und die Herkunft einzelner Komponenten vor jeder Wiederverwendung prüfen. Auch OPL3GM und seine Abhängigkeiten separat lizenzrechtlich prüfen. **Zunächst nur Verhalten, Klang und Bedienkonzept vergleichen; keine fremden Quelltexte ohne geprüfte Kompatibilität übernehmen.** Original-ROM/SBK und proprietäre FM-Patch-Daten nicht unautorisiert verbreiten. Vergleichsmetriken: registergenaue FM-Audioausgabe, Instrumenten-Mapping und Velocity, Voice-Stealing, Effekte/Routing, DAW-Automation, Plugin-State und reproduzierbare Windows-VST3-Tests.

## Vor Implementierung zwingend nachweisen

Der derzeitige EMU8000-/86Box-Pfad nutzt eine begrenzte **24-Bit-Sample-Adressierung**; in `src/engine/Synth.cpp` und `src/engine/Emu8000Box.cpp` werden Grenzen durchgesetzt. Ein simples Anheben von `m_chipRamKb` oder `28672` auf `1048576` kann daher **nicht** 1 GiB adressierbaren Chip-RAM schaffen. Vorab Architekturvarianten vergleichen (Sample-Virtualisierung / Fensterverwaltung / Änderungen an der emulierten Adressierung) und Folgendes messen: 32-Voice-Audio-Sicherheit, keine page faults/Allokationen im RT-Callback, reproduzierbare Preset-/Projektzustände, SF2-Kompatibilität, RAM-Grenzen, Sampleloops an Fenstergrenzen, Korrektheit der Hardware-Filter/Interpolation und Klangvergleich Classic vs. Extended bei identischen Samples.

**Ausdrücklich keine aktuelle Entwicklungsfreigabe für WAV-Import oder 1-GiB-Erweiterung.** Späterer Auftrag separat nach erfolgreichem Abschluss der klassischen AWE32/AWE64-Version.
