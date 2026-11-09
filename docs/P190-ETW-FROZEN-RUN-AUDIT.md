# P190 – unabhängige ETW-Ursachenanalyse (nur Audit)

Eigener Branch audit/p190-rt-etw-20261109, unveränderter P190-Produktstand bc565cfc238ece6f59af6ef6e7cc950136688b8d.

Eingefrorene Belege aus [Windows-Run #42571191825](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42571191825), Original-Artefakt 13653961116. Funktionale Prüfung 67/67 CTests, 537 Validator, 99 GUI, Test Lab TECHNICAL_PASS. Realtime: **FAIL 1/14.400**: 128 Frames, 30 kontinuierlich gehaltene Stimmen, Szenario 4 (Filter- und Effekt-Automation, ohne konkurrierenden Save/Recall-Thread), Block 1: **4.603,2 µs** bei **2.902,49 µs** Budget. Median derselben Zelle 1.540,7 µs; 99. Perzentil 2.427,1 µs; Thread start core 2, end core 1. Diese Beobachtung allein beweist KEINEN Scheduler- oder DSP-Fehler.

Der Trace wurde tatsächlich als GeneralProfile ETL archiviert: etw-status.json recorded=true, analyzed=false; Größe ca. 305 MB. Die Audit-Workflow übernimmt nach Hash-/SHA-Prüfung ausschließlich diese eingefrorenen Daten, keinen neuen Performance-Test, und baut den in P171 bereits verwendeten TDH-CSwitch-Decoder. Per echtem Windows-WPR-Sleep-/Busy-Positivkontrolllauf prüft sie Decoder und Zeitbasis und rekonstruiert die komplette on/off-CPU-Zeit jedes Produkt-Callbacks. Schedulerpreemption wird NUR bei vollständiger ETW-Abdeckung und korrekter CSwitch-Zustandsdekodierung als Ursache klassifiziert. Ein fehlgeschlagener Kontrolllauf bleibt FAIL/UNKNOWN und wird nicht als Erklärung umetikettiert.

Die ETW-Untersuchung ändert weder SoundFont-Filter, Effekt-Mixer noch VST3 und ersetzt keine reale DAW/ASIO-Abnahme. RELEASE NO-GO, unabhängig von der Analyse.

## Verifiziertes kausales ETW-Ergebnis (09.11.2026)

[Unabhängiger Windows-Audit #42574064788](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42574064788) **SUCCESS**. Originaldaten der produktiven P190-Run #42571191825 wurden SHA-geprüft und unangetastet dekodiert; ETW-Verlustzähler: `events_lost=0`, `buffers_lost=0`, Decoder-Kalibration mit separaten echten Sleep-/Busy-Kontrollen: **PASS**. **14.400 von 14.400 Callbackintervallen vollständig**, nur **1** Deadline-Überziehung.

**128 Frames · 30 Stimmen · Filter-/FX-Automation · 2. Audioblock**: 4.603,3 µs Callback, Budget 2.902,49 µs. Davon **3.935,7 µs scheduled/on-CPU**, **667,6 µs off-CPU**, **363,9 µs Ready-Preemption**, **0,0 µs Waiting**; Start CPU 2, Ende CPU 1. Kalibriertes Urteil `SCHEDULED_RUNTIME_OVER_BUDGET_NOT_PURE_DSP_PROOF`.

**Schlussfolgerung:** Dieser Ausreißer ist NICHT durch bloßes Hinzuzählen der gemessenen Scheduler-Wartezeit erklärt. Selbst die On-CPU-Zeit übersteigt das Budget um etwa 1.033,2 µs. Scheduled/on-CPU enthält aber unbekannte Anteile von Interrupts/Systemzeit; das belegt **keinen spezifischen DSP-Implementierungsfehler**. PCM, korrekter Effekt-Nullpunkt, Filter-Mathematik und die bestehende technische VST3-Abnahme bleiben unverändert erfolgreich. Für eine Audio-Performance-Optimierung ist eine gezielte Hotspot-/Same-Runner-A/B-Untersuchung des 128-Frame-/30-Stimmen-/Modulationspfads notwendig. **ASIO und reale SoundFont-/ROM-Klangparität weiterhin NOT RUN, Release NO-GO**.

Den vollständigen Befund und verbindliche Akzeptanzbedingungen enthält [Issue #94](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/94). Der Audit-Quellzweig ändert **keine** Produktions-DSP-Datei.
