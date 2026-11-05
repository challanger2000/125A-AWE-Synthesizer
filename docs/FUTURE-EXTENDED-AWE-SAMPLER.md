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

## Vor Implementierung zwingend nachweisen

Der derzeitige EMU8000-/86Box-Pfad nutzt eine begrenzte **24-Bit-Sample-Adressierung**; in `src/engine/Synth.cpp` und `src/engine/Emu8000Box.cpp` werden Grenzen durchgesetzt. Ein simples Anheben von `m_chipRamKb` oder `28672` auf `1048576` kann daher **nicht** 1 GiB adressierbaren Chip-RAM schaffen. Vorab Architekturvarianten vergleichen (Sample-Virtualisierung / Fensterverwaltung / Änderungen an der emulierten Adressierung) und Folgendes messen: 32-Voice-Audio-Sicherheit, keine page faults/Allokationen im RT-Callback, reproduzierbare Preset-/Projektzustände, SF2-Kompatibilität, RAM-Grenzen, Sampleloops an Fenstergrenzen, Korrektheit der Hardware-Filter/Interpolation und Klangvergleich Classic vs. Extended bei identischen Samples.

**Ausdrücklich keine aktuelle Entwicklungsfreigabe für WAV-Import oder 1-GiB-Erweiterung.** Späterer Auftrag separat nach erfolgreichem Abschluss der klassischen AWE32/AWE64-Version.
