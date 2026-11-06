# P131 – Processor-Laufzeitprofil ohne ASIO-Freigabe

**Stand:** 6.11.2026. **Branch:** `audit/p131-process-wall-cycles-20261106`; Ausgangsbasis P130 `f1b722a7`. **Produktionscode unverändert.**

## Ziel

Die seltenen Zeitbudgetüberschreitungen der vorherigen P128/P129-Messungen auf geteilter Windows-VM gezielt beobachten, ohne sie vorab der DSP-Rechenzeit oder einer Mutex-Blockade zuzuschreiben.

Der C++23-Test `tests/p131_process_wall_cycles.cpp` kompiliert den echten `Factory.cpp`-VST3-Processor mit dem festgehaltenen Steinberg SDK 3.8.1 und synthetischer öffentlicher ROM/SF2. Er erzeugt **neun Szenarien mit jeweils 500 realen `process()`-Callbacks**, 44,1 kHz:

- 128, 256, 1024 Frames
- Render ohne zusätzlichen Worker, konkurrierende V10-Saves, konkurrierende V10-Saves + Recalls

Vier NoteOn-Ereignisse treffen jeden Audioblock, einschließlich direkt nach einem Recall. Ein Mindestanteil hörbarer Blöcke verhindert stille Scheinergebnisse. Der Kontrollthread läuft mit einer nominellen 15-ms-Kadenz; sämtliche Calls zählen tatsächliche erfolgreiche Saves und versuchte/akzeptierte Recalls.

## Instrumentierung

- `QueryPerformanceCounter`: echte **Wandzeit ausschließlich um `process()`**, in Mikrosekunden; Zeitbudget ist `frames / 44100`.
- `QueryThreadCycleTime`: zusätzlich **rohe Windows-Thread-Zyklen** pro Aufruf (mit Validitätsfeld), ohne Scheinumrechnung in CPU-Millisekunden. Die vormals unplausiblen `GetThreadTimes`-Einzelwerte werden nicht verwendet.
- `GetCurrentProcessorNumber`: Kernnummer vor und nach Callback als Diagnose von Migration. QPC und Zyklen können durch VM, Frequenzregelung, Migration und Messaufrufe verfälscht werden; selbst gleichzeitige Spitzen beweisen keine eindeutige Ursache.
- Pacing durch `sleep_until` erfolgt **vor** dem Start der Wandzeitmessung. Scheduler-Wakeup-Latenz wird damit nicht als `process()`-Laufzeit bezeichnet.
- CSV: **jeder einzelne** Callback mit Puffergröße, Szenario, Index, Wandzeit, Deadline, Überschreitung, Rohzyklen, Zyklenstatus, Kernwechsel und hörbarem PCM; zusätzlich je Fall Median/p99/Maximum und Häufigkeit.

## Testabnahme und Grenzen

Die CTest-Prüfung muss vollständige neun Szenarien mit hörbarem PCM und tatsächlichen Save-/Recall-Aufrufen liefern. Sie **darf nicht** aufgrund eines fehlenden Deadlineausreißers als ASIO-/RT-GO interpretiert werden: P131 ist die Vollständigkeitskontrolle einer Messung. Auch bei nachgewiesenen Überschreitungen ist ein CTest-Erfolg möglich, weil es um nachvollziehbare Rohdaten geht; diese müssen separat ausgewertet werden.

Erst nach Prüfung der neuen Windows-Actions-Belege können Ursachenhypothesen bewertet und gegebenenfalls gezielte Produktkorrekturen erstellt werden. Keine Codeänderung an Chip, DSP, Chorus, Filter oder MIDI ohne unabhängigen Nachweis.

**Echter ASIO-DAW-Betrieb auf dem Zielrechner: NOT RUN. Hardware-Chorusvergleich: NOT RUN. RELEASE-/GUI-NO-GO.**
