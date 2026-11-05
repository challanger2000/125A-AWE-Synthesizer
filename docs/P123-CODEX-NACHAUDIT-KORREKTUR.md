# P123 — Codex P122-Nachaudit: Korrekturkandidat und verbindliche Gegenprobe

**Stand 2026-11-05. Keine GUI- oder Release-Freigabe.**

- Codex-Nachaudit am P122-HEAD `23867361dc3a58887f7586b7d3b727de04740107` meldete **zwei hohe** und **zwei mittlere** offene Fehler.
- Kandidat P123: `d91fa26b67aac23616265c741d93353ff0b500a2` auf **demselben** Branch `fix/p122-bank-dirty-audit`.
- [Windows Actions #42045162465](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42045162465): **34/34 CTests PASS, 47/47 Steinberg VST3 Validator PASS, 3/3 echte EditorHost GUI-Smokes PASS**. Die CTests umfassen die modifizierten `p122_rt_state_snapshot`, `p122_vst3_bank_host` und `p121_pitchbend_audio` mit synthetischem ROM.
- Der allererste P123-Build scheiterte an einem unqualifizierten `VxdPanClock`-Namen. Der C++-Namespace ist im oben genannten Kandidaten korrigiert. Nur der letzte vollständige Windows-Lauf darf als PASS bezeichnet werden.

## Festgestellte Fehler und Kandidatenkorrekturen

1. **HOCH / mehrerer Writer erzeugen persistente Mischzustände:** Die P122-Lösung mit unabhängigen `audio`- und `control`-Zählern schützte nur Leseintervalle, nicht gleichzeitig verändernde Writer. Codex: 51/30.000 Fälle, darunter unzulässige Kombinationen der Kanalprogramme; diese ließen sich sogar in einen neuen Processor laden. P123: `RealtimeStateVersion` serialisiert die *kurzen* Multi-Parameter-Transaktionen mit einer atomaren Gate/Generation. Control/Recall darf auf das Ende eines RT-Schreibvorgangs warten, aber der Audiothread hat lediglich einen einzigen nichtblockierenden CAS-Versuch. Tritt ein Konflikt auf, hat Recall Vorrang. Produktiver VST3-Stress: `tests/p122_vst3_bank_host.cpp`; gemeinsamer Zustands-Orakeltest: `tests/p122_rt_state_snapshot.cpp`. **Unabhängige Original-Codex-Reproduktion noch NICHT WIEDERHOLT.**

2. **HOCH / getState scheitert während Playback:** Codex: 91/500 Saves bei einer klingenden Stimme ohne Automation fehlgeschlagen. P122 markierte *den ganzen Audioblock* als Writer. P123 markiert nur tatsächliche Änderungen gespeicherter Felder, nicht die Soundberechnung. `tests/p122_vst3_bank_host.cpp` führt 500 reale VST3-Saves während paralleler `process(128)`-Aufrufe **ohne proprietäres ROM und ohne echte klingende Stimme** aus. **Codex' originale 1-Stimmen-Messung bleibt NOT RUN**, daher keine endgültige Freigabe.

3. **MITTEL / VXD Pan-Glide hängt von 48/96-kHz-Hostrate ab:** Die 227 EMU8000-Chip-Frames werden jetzt mit rationaler Restübertragung in Hostframes umgerechnet (`src/engine/VxdPanClock.h`, `Synth.cpp`). `tests/p121_pitchbend_audio.cpp` vergleicht tatsächliche PSST-Panoramaregister nach genau 50 ms bei 44.1/48/96 kHz an synthetischer ROM. Die bestehenden Blockpartitionstests bleiben aktiv.

4. **MITTEL / Bankfehlermeldung bleibt trotz erfolgreicher Retry:** `PresetBrowserView::Select` invalidiert nach erfolgreichem Verbindungs-Retry den zuvor lokal angezeigten Fehlerhinweis und zeichnet wieder den aktuellen zentralen Audiostatus. Ein ausdrücklich fehlender End-to-End-GUI-Fehler-zu-Erfolg-Maustest ist noch **NOT RUN**. Keine pauschale GUI-Freigabe daraus ableiten.

## Unverändert bewahrte P122-Korrekturen

- Zero-Sample-Pitchbend.
- RPN/Pitchbend-Range-Retuning.
- Blockgrößen-unabhängiger Win95-Pan-Verlauf.
- Sende-Fehler blockiert vorgetäuschte Browser-Auswahl.

## Notwendiger unabhängiger Abschluss-Codex-Audit (READ ONLY)

Auf **exaktem** Kandidaten `d91fa26b67aac23616265c741d93353ff0b500a2`, keine Repositoryänderungen:
- Die originale 51/30.000-Writer-/Recall-Reproduktion mit echten VST3-Processor-Instanzen und Kontrollzustands-Reload vollständig wiederholen; **0 Mischzustände** verlangt.
- Die originale 91/500-getState-Reproduktion mit 1 **wirklich klingenden** Stimme ohne Automation durchführen; **500/500 erfolgreiche Saves**, keine Deadline-Verletzungen. Ebenso 16/30 Stimmen und dense Automation, plus Last-/Wait-Fairness.
- Pan-Glide bei 44.1/48/96 kHz einschließlich wechselnder VST3-Blockgrößen anhand tatsächlicher Audio-/PSST-Zeitbasis überprüfen.
- Browser: fehlgeschlagene Same-Bank-Re-Select-Nachricht, erfolgreiche Wiederverbindung, korrekte Audio-Bank, gespeicherter Zustand und nicht mehr roter Fehlertext – echter VSTGUI-Pfad.
- Eigene neue Gegenbeispiele suchen: konkurrenzbedingtes Überspringen von MIDI-Events während Recall, Semantik von Programmwechseln gegenüber jüngstem Recall, Zero-Sample-, Stop/Start- und Enginewechsel-Grenzen.
- Ergebnisse jedes Gates eindeutig als PASS/FAIL/NOT RUN; die 34/34 CTests sind keine Behauptung über den gesamten ursprünglichen Fehlerraum.

**Bis unabhängige Reproduktion und explizite Entscheidung: GUI-NO-GO.** Release bleibt NO-GO wegen zusätzlich offener Original-Asset-, echter DAW- und Hardwarevergleichs-Prüfungen. Hardware-Klanggleichheit allein ist keine Voraussetzung für einen späteren GUI-Start.
