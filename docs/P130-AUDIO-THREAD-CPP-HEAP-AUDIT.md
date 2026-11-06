# P130 – begrenzter C++-Heap-Audit auf dem echten VST3-Audiothread

**Stand 6. November 2026.** Ausgangscommit des Produktivcodes: `a07ecc5757629276de4a3a5c8fb5a25f9a4b161c`, Branch `fix/p122-bank-dirty-audit`. P129-CPU-Optimierungen enthalten. Dies ist **kein** Nachweis der ASIO-Deadlinefreigabe.

## Testgegenstand

Der P130-Prozessor-Audit verwendet den **echten produktiven `Factory.cpp`-`Processor`**, über denselben bewährten Extraktor wie die P128-State-/Bank-Regressionen, kompiliert mit dem festgehaltenen Steinberg SDK auf Windows 2022. Die aktive Emu8000Box-Engine verarbeitet eine **synthetische, selbst erzeugte ROM/SF2**; keine echten kommerziellen Assets.

Der Test markiert ausschließlich den aufrufenden Audiothread während `Processor::process()` und erfasst die globalen C++-`operator new` / `operator new[]`-Aufrufe. Host-seitiges Erstellen von Testevents, Erstellung und Aktivierung der Synthengine, ROM/SF2-Initialisierung, Speichern auf einem Controlthread und Ausgabe der Logs erfolgen **außerhalb** der Messklammer.

In fünf getrennten Szenarien werden je 240 vollständige 1.024-Frame-Callbacks bei 44,1 kHz ausgeführt:

1. Kein MIDI-Event, digitale Stille
2. Vier echte MIDI-NoteOns in regelmäßigen Abständen, laufendes Audio
3. 30 NoteOns in jedem Audioblock, echtes Audiosignal
4. ProgramChange, kanalbezogener ProgramChange, Master- und GUI-Automation plus MIDI
5. 128 dicht stehende Pitchbendpunkte pro Audioblock mit weiter klingenden Noten

## Nachweis

[Windows-Actions #42183513314 – SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42183513314): **0 Aufrufe, 0 Bytes** für `new` / `new[]` in **1.200/1.200** überprüften Callback-Ausführungen. Die vier tönenden Szenarien produzierten in 239–240 ihrer jeweils 240 Blöcke PCM-Audio. Das originale Testprotokoll und der gepinnte SHA liegen im Artefakt `P130-Actual-AWE-Processor-CPP-Heap-Audit`.

Ab jetzt ist `125A_p130_no_cpp_new_on_audio_thread` als CTest der Windows-Produktion eingebunden und soll künftige versehentlich eingeführte C++-Heap-Allokationen im Audiothread erkennen. Ein FAIL ist eine Entwicklungsregression, kein Anlass, die Instrumentierung aus dem Test zu entfernen.

## Grenzen – keine unbelegten Aussagen

- Die globalen C++-Operatoren zählen keine Aufrufe von `malloc/calloc/realloc`, Windows-`HeapAlloc`, Memory-Mapping oder anderen sekundären Allokationspfaden.
- Fremde Threads werden nicht gemessen; nur die `process()`-Aufrufklammer des jeweiligen Audiothreads.
- Eine erfolgreich abgeschlossene Instrumentierung beweist nicht Mutex-/Thread-Blockierungsfreiheit, null DPC-Latenz, stabile ASIO-Terminierung oder das Timing aller Host-/Plugin-Kombinationen.
- Der Windows-GitHub-Runner ist **nicht** der reale Fender-Studio-Pro-/Studio-One-Zielhost. Die frühere P129-A/B-Lastmatrix [#42181915013](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42181915013) fand unregelmäßige Deadlineüberschreitungen trotz schnellerem P129-Median.
- Die separat vorbereitete Chorus-Quantisierung [Draft PR #67](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/67) ist nicht Bestandteil dieser Teständerung und bleibt ohne Hardware-Referenz ungemergt.

**Entscheidung:** Das C++-`new`-Teilkriterium ist nachgewiesen. **Release und ASIO-Deadline bleiben NO-GO**, bis die anderen unabhängig definierten Gates erfüllt sind.
