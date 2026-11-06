# P137/P138 – verworfenen Legacy-Float-DSP im EMU8000 86Box-Modus vermeiden

**Datum:** 6. November 2026. **Entwicklungsbranch:** `fix/p122-bank-dirty-audit`. **[P137-PR #75 gemergt](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/75)**, Mergecommit `c276fd970f22721f930b5effb13d38bab6d86cf2`; Original-Produktionsänderung `443b1d3dd55b1dd070f11ebe30f618a825e16d75`. Releasestatus **NO-GO**.

## Gefundene echte Doppelarbeit

Im ROM-gestützten `Chip::Box86`-Modus führt `Emu8000Core::RenderBlock()` bei 44,1 kHz für **jedes** native Sample nacheinander `RenderNative(&l,&r,1)` und `m_box.RenderFrame(il,ir)` aus. Nur das int32-Ausgangssignal aus `m_box.RenderFrame()` wird tatsächlich in das Plugin-PCM geschrieben; die alte Float-Audiosynthese in `RenderVoice()` mit separater Sample-Interpolation, Filterberechnung, Gain/Pan und FX-Sends wird nach der Berechnung verworfen.

Eine Doppelberechnung ist direkt aus dem Quellcode belegt, nicht aus vermeintlichen CPU-Prozentwerten abgeleitet. Die P135/P136 realen Windows-ETW-Samples enthalten hohe Anteile in `Emu8000Core::RenderVoice` neben `emu8k_update_chunk` und ihren Hilfsfunktionen. Das ist **kein** Nachweis eines Datenrennens, aber ein technisch begründeter CPU-Arbeitsreduktionskandidat.

## Exakte Optimierung

`src/engine/Emu8000.cpp` `RenderVoice()` prüft **nach** den unveränderten Modulationshüllkurven, der Volumenhüllkurve, den beiden LFOs und der Pitch-Berechnung `if(m_chip == Chip::Box86)`. Nur im 86Box-Modus wird mit **derselben** früheren Fließkomma-`increment`-Berechnung, derselben uint64->16.16-Fortschreibung und derselben Loop-Wrap-Operation die Schatten-Sampleposition `vs.address/vs.frac` fortgeführt und anschließend das verworfene Float-Sample/Filter-Audio übersprungen.

**Nicht übersprungen** werden Envelope-/LFO-/Mod-/Pitch-Zustand, Register-Schattenwerte, `UpdateRegistersFromState()`, der 86Box-DSP, die echte Hardwarefilterung, Reverb, Chorus, EQ, MIDI- oder V11-State. Die bestehende Legacy-Rendererberechnung für nicht-86Box-Chipmodi ist unverändert. Kein neuer Heap, Mutex, Warte-/Threadpfad und keine neue Effektmathematik.

## Vollständiger Klang-/Zustands-Nachweis

**[P137 Windows #42233912768 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42233912768)**. Die vorherige echte, gepinnte P134-V11-VST3-Binärdatei aus [Run #42221403709](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42221403709) und die aktuelle P137-Binärdatei wurden auf **demselben** Windows-2022-Runner per echter Steinberg-IComponent/IAudioProcessor-Schnittstelle geladen.

**1.474.560 Stereo-Frames = 11.796.480 32-bit-Float-PCM-Bytes bitgenau identisch**, plus **identische V11-Save-State-Streams nach sämtlichen 3.072 Vergleichsblöcken**, 128/256/512/1024 Frames, 1/16/30 angesetzte Stimmen, dichte MIDI-/Pitchbend-/Bank-/Program-Automation, alle 64 Creative Reverb-/Chorus-Moduskombinationen mit aktiven Wet-Sends, wiederholter Projekt-Recall. Der separat korrigierte CC120-Stopp aus P134 wurde weiter erfolgreich durch eigenen echten VST3-Test kontrolliert.

**45/45 CTests**, **47/47 SDK-interne Validatorchecks**, **537/537 vollständige eigentliche Steinberg VST3-Modulprüfungen**, **3/3 Win32-EditorHost-GUI-Tests**. Keine neuen Warnungen in der Release-Grenze bekannt.

## Unabhängiger gleichzeitiger Vorher-/Nachher-Leistungsvergleich

**[P138 Windows #42235001686 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42235001686)**. Gleiche beiden echten P134/P137-VST3-Binärdateien; 44,1 kHz, **128 Samples, 30 synthetisch gestartete und durchgehend gehaltene Noten**. Vier alternierende ABBA-Sets, **jeweils 4.800 tatsächliche `process()`-Callbacks pro Binärdatei**, Ausführung auf derselben Windows-2022-VM, QPC ausschließlich um die Audio-`process()`-Funktion. Der Host protokolliert die Einzelzeiten aller Aufrufe, nicht nur Mittelwerte, und prüft jedes ausgegebene PCM-Paar und den abschließenden V11-State bytegenau. Die Zahl der physischen Chipstimmen wird in diesem minimalen, uninstrumentierten A/B-Host nicht getrennt gezählt; der identische synthetische 30-NoteOn-Seed ohne anschließenden NoteOff plus hörbare, bitidentische PCM-Blöcke sind belegt.

| Kennwert, µs, Audiobudget 2.902,494 µs | P134 vorher | P137 nachher |
| --- | ---: | ---: |
| Median | 1.922,0 | **797,9 (−58,5 %)** |
| P99 | 2.048,6 | **905,0 (−55,8 %)** |
| Maximum | 3.408,6 | **2.128,3** |
| Budgetüberschreitungen pro 4.800 Aufrufe | 2 | **0** |

**P138:** 46/46 native CTests einschließlich dieses neuen ABBA-Benchmarks, 537/537 vollständige VST3-Validatorchecks und 3/3 GUI-Smokes. Das Original-CSV `p138-stable-abba-128x30.csv` und die zusammenfassenden Messwerte liegen im Actions-Artefakt `P138-Box86-ShadowDSP-4800-ABBA-FX-V11-Regression`.

**Vorsicht bei der Interpretation:** Das ist ein kontrollierter **Offline-VST3-QPC-Durchsatzvergleich**, nicht die vollständige ETW-Deadline-/MMCSS-/ASIO-Prüfung auf dem Anwenderrechner. Vergleichsreihenfolge und musikalische Testlast wurden kontrolliert, aber nicht alle Shared-Runner-Schwankungen, Treiberlatenzen, übergroßen echten SoundFont-Bänke und komplexe DAW-GUI-Interaktionen. Der gemessene CPU-Gewinn ist belastbar für diese Testpopulation, **kein Beweis allgemeiner 0-Ausreißer-Garantie**.

## Separates weiteres Echtzeit-Gate

**Bisher P135/P136 auf P134-Basis:** [P136 unabhängige Rohdatenrequalifikation SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42232742206): 414 von 201.600 echten Audiocallbacks zu langsam, darunter 256/172.800 in fünf ursprünglichen P132-Modi und 158/28.800 im zusätzlichen P133-FX-Lastmodus. Trotz 46/46 CTests, 537/537 Validator und 3/3 GUI auf beiden VMs eindeutiges **Echtzeit-FAIL**, Zielrechner-ASIO **NOT RUN**.

Um diese Last nun auf dem optimierten **P137** zu testen, wurden auf separatem [P139-Auditbranch](https://github.com/challanger2000/125A-AWE-Synthesizer/tree/audit/p139-p137-v11-full-etw) wieder alle **72 Zellkombinationen × zwei Profillaufarten × zwei unabhängige Windows-Runner** eingerichtet. Erst vollständige ETW-/Heap-/lastgleiche Ergebniserfassung und unabhängige Abnahme ermöglicht neues Echtzeiturteil. P139 ändert keine Produktdateien. **Keine Releasefreigabe, kein Gumroad-Paket.**
