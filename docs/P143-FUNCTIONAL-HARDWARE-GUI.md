# P143 – Funktionales VSTGUI-Hardwarelayout vor dem Skin

**Quelle:** `feature/p142-compact-vstgui-main-edit-browser` bei `d451006be18e73b74ed7c397067723e0b84f86c4`. 1000 × 640 logische VSTGUI-Pixel, Windows x64, VST3; unabhängig von DSP und Preset-Speicherformat.

## Verbindliche Bedienstruktur

- **MAIN:** Reverb Send links, Chorus Send direkt daneben, ein **deutlich groesserer Master Volume rechts**. Die acht Original-Creative-Typen von Reverb und Chorus sind jeweils nur ueber einen kleinen, direkt zugeordneten Pop-up-Selektor erreichbar.
- **EDIT:** AMP ENVELOPE mit Attack/Decay/Sustain Reduction/Release, FILTER ENVELOPE mit denselben vier Kontrollen und FILTER TONE mit Cutoff Reduction/Resonance Boost. MOD RESET setzt ausschliesslich alle 12 SoundFont-Offsets (inklusive Sends) auf 0; Master, Bank, Preset, ROM und SF2 bleiben unangetastet.
- **BROWSER:** eigene einblendbare VSTGUI-Seite mit Filter, Suche, Scrollliste und Host-Preset-Selektion. Keine staendige grosse Browser-Spalte.
- **Gemeinsame Navigationszeilen:** Bank vor Preset, PREV/NEXT, ROM LOAD, SF2 LOAD und Statusinformationen bleiben ohne Seitenwechsel erreichbar.
- **Master Volume** gehoert NICHT in einen FX-Bereich. Vollstaendig rechts, eigenstaendiger Host-Parameter, Unity bei 100 % und VSTGUI-Ctrl-Klick setzt ihn unabhaengig zurueck.
- **Effekt-Typen** sind originale V11-Presetparameter 1200/1201, keine erfundenen oder rein dekorativen Menueintraege.

Die sichtbaren Fensterkoordinaten sind in `PresetBrowserView.cpp` festgelegt. Die Parameter-IDs 1000/1002, 1003, 1100–1111 und 1200/1201, Projektzustand V11 sowie Echtzeit-DSP bleiben unangetastet.

## Getrennte Gestaltungsebene

Dies ist absichtlich **kein fertiges schwarzes/goldenes Hardware-Skin**. Der naechste Schritt verwendet die freigegebene visuelle Vorlage mit bernsteinfarbenem Display, originalem 125A-Masterlogo, echten Leiterbahn- und Kondensator-Dekorationen und abgestuften Metallreglern. Faceplate-Zeichnung, Knob-Paint und spaetere Bitmap-/Vektorressourcen koennen ausgewechselt werden, ohne in `valueChanged`, `ChangeParameter`, `Select`, ROM/SF2-Ladeaktionen oder Projekt-Recall einzugreifen. Dekoration bekommt kein Mouse-Hit-Testing.

## Verifikation / offene Punkte

- Strukturvertrag: `tests/p14_vstgui_contract.py` prueft konkrete Bereiche und unveraenderte Verknuepfungen.
- Physischer Windows-Test: `tools/p143_hardware_layout_acceptance.py`, via `.github/workflows/p143-functional-hardware-gui-windows.yml`. Maus-Drag, Default-Reset, Effektwahl, Bank/Preset, Browser, Dialogabbruch und GUI-Lebenszyklus muessen erneut erfolgreich sein.
- Keinen Release behaupten, bis P143-Build, Steinberg-Validator und EditorHost bestandene Ergebnisse liefern.
- **Nicht abgeschlossen:** finaler schwarz-goldener Skin, durchgehendes Host-/VSTGUI-Zoom bzw. stufenloses Resizing, Nachweis in kommerzieller DAW und ASIO-Hardware. Die feste 1000 × 640-Oberflaeche ist noch kein belegtes Zoom-Verhalten.
