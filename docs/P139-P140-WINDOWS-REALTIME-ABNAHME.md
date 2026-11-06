# P139/P140 – Abschluss des Windows-Echtzeit-Laboraudits für die P137-Optimierung

**Stand:** 6. November 2026. **Echter VST3-Audio-Prozessor auf Windows 2022, 44,1 kHz.**

**Produktionsstand:** `fix/p122-bank-dirty-audit`; die optimierte P137-Implementierung ist bereits durch [PR #75](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/75) mit Merge-Commit `c276fd970f22721f930b5effb13d38bab6d86cf2` integriert. Kein neuer DSP-Merge dieses Berichts. Im Entwicklungsstand enthalten: P132-F01 verteilt die originale 980-Frame-Chipberechnung; P134 stoppt mit CC120 das physische Lautstärkeziel der Stimme; P133 erhält alle 8×8 realen Creative-FX-Presets und das rückwärtskompatible V11-Projektformat.

## 1. Vollständiger unabhängiger ETW-Echtzeittest P139

Für die reproduzierbare P139-Untersuchung wurden die echten normalen und passiv instrumentierten Windows-VST3-DLLs aus dem **unveränderten P137-Produktionsquellstand `f0f397c265db4db145571b89d86676361d8514ae`** neu gebaut. Die Diagnostik war auf einem getrennten Auditbranch unter `audit/p139-p137-v11-rt-stress` und wird nicht in den produktiven Plugincode gemergt. Die Workloads basieren auf den Originalfällen P135/P132 und ergänzen die aktive Creative-FX-Automation.

**Abgeschlossene unabhängige Windows-2022-Runs:**

- [P139 Windows A – #42236380915 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42236380915).
- [P139 Windows B – #42236381113 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42236381113).

| Kennzahl | Windows A | Windows B | Summe |
| --- | ---: | ---: | ---: |
| Vollständig gemessene echte `process()`-Callbacks | 100.800 | 100.800 | **201.600** |
| Überziehungen des jeweiligen 44,1-kHz-Audiobudgets | **0** | **0** | **0** |
| Davon in identisch-stimmig besetzten Blöcken | 0 | 0 | **0** |
| CTest (inkl. P133/P134, reale VST3-PCM-Census-Prüfungen) | 46/46 | 46/46 | PASS |
| Echter Steinberg-Modulvalidator | 537/537 | 537/537 | PASS |
| Win32-EditorHost-Smokes | 3/3 | 3/3 | PASS |

Jeder Runner prüfte **72 Lastzellen pro Messpass**: **128/256/512/1024 Samples × 1/16/30 aktive Stimmen × sechs Modi** – 5 historische P132/P135-Lastarten und neu ein sechster Modus mit P133 8×8 Reverb/Chorus-Wahl, FX-Sends, dichter MIDI-/Parameterautomation und parallelem V11-Save/Recall. Für jede Zelle wurden die Audiozeiten auf dem realen VST3-Prozessor gemessen; die geprüfte Trace-Population umfasst **je 50.400 Rückrufe mit und ohne ETW** pro Runner.

Die CPU-ETW-Ereignisse wurden auf die einzelnen `process()`-Zeitfenster zurückgeführt. Die Profilaufzeichnung wurde durch Schlaf-/Busy-Positivkontrollen plausibilisiert; die Heap-Messung durch echte WPR-Heap-Positivkontrollen kontrolliert. **Im separat überwachten Audiopfad traten keine Heap-Ereignisse auf.** Normale Echtzeitlast und Diagnose-Build lieferten gleiche PCM-Puffer; der ursprüngliche P137/P134 Vollabgleich hat zusätzlich 11.796.480 Float-PCM-Bytes und sämtliche V11-Zustandsdaten als bitidentisch geprüft.

**Bewertung der P139-Labormessung:** `PASS_IN_WINDOWS_LAB_ONLY` (0/201.600 Deadlinefehler), keine Freigabe realer ASIO-/MMCSS-Aufnahme-/Wiedergabebedingungen.

## 2. P140 – identischer Rechner, reale alte/neue VST3-DLLs im ABBA-Muster

Zwei getrennte Windows-CI-Zuteilungen von P135 und P139 sind grundsätzlich **nicht** für einen kausalen Performance-Vergleich geeignet (VM-/Scheduler-/CPU-Unterschiede). Deshalb wurde ein ergänzender **Same-Runner-P140** ausgeführt:

- [P140 Windows – #42239176126 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42239176126), reproduzierbarer Diagnosecode in [Draft PR #77](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/77) (Audit-only, nicht mergen).
- Die **wirkliche alte P134-V11-DLL** stammt aus dem archivierten [P135-Run #42227962225](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42227962225), Commit `b249b110f1f0117e25757dc4001dc628d6b57d37` (das ursprüngliche P135-Resultat war nur durch einen Fehler im Python-Auswerter ROT; unabhängiger Nachweis über [P136 #42232742206](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42232742206)).
- Die **wirkliche neue P137-V11-DLL** wurde aus unverändertem P137-Produktionscode gebaut und ebenfalls passiv diagnostiziert; alte `p135ReadVoices`-/`p135HeapControl`-Exporte wurden nur im externen Host berücksichtigt.
- Reale Windows-VST3-Calls, **128 Samples, 30 vorgespielte und im Chip gezählte Stimmen, 44,1 kHz**, ABBA-Aufrufreihenfolge `P134 – P137 – P137 – P134`, die fünf Lastarten **0/1/2/4/5**, also Rendering, paralleles Save, Save+Recall, dichte MIDI-Automation und neue FX-Umschaltung mit gleichzeitigem V11-Save/Recall. **Je Version 20.400 Callbacks; 40.800 insgesamt**, keine unterfüllten oder verspäteten Werte aus der Gesamtpopulation herausgefiltert.

| Originale und optimierte Version auf **demselben Rechner** | P134 vorher | P137 nachher |
| --- | ---: | ---: |
| Vollständig gemessene echte `process()`-Callbacks | 20.400 | 20.400 |
| **Deadlineüberschreitungen, vollständige Population** | **58** | **0** |
| Davon bei vollständig lastgleichen aktiven Stimmen | **16** | **0** |

Die optimierte Version erzeugte **keine einzige Deadlineüberschreitung in den 20.400 P140-Paarvergleichsblöcken**. Die alte P134-Version erzeugte auf demselben Runner 58; davon traten 16 unter tatsächlich passender Stimmenlast auf. Die getrennte P138-Dauernoten-ABBA-Messung erbrachte zusätzlich den belastbaren Median-/P99-Gewinn **1.922 µs → 797,9 µs (−58,5 %) bzw. 2.048,6 µs → 905 µs (−55,8 %)**, bei bitidentischem PCM.

**P140 prüft bewusst nur die 128/30-Lastfälle.** Die übrigen Frame-/Stimmenkombinationen sind durch den vollständigen P139-Lauf abgedeckt; daraus werden keine gepaarten A/B-Aussagen abgeleitet. Zwei gleiche GitHub-VM-Zuteilungen sind ebenfalls kein exaktes physisches ASIO-Zielrechnerlabor.

## 3. Abnahmeentscheidungen

- **Funktionale Windows-VST3-Regression:** PASS (46/46 native CTests; 537/537 realer Steinberg-Validator; 3/3 GUI-Smokes in P139).
- **Aktuelle Performance-Verbesserung P137 unter Last:** PASS im gepaarten Windows-Labor (P140 alt 58/20.400 gegen neu 0/20.400, davon matched 16 → 0; P138 −58,5 % Median).
- **Vollständige unabhängige Windows-Stressmatrix:** PASS in den gemessenen P139-Szenarien (0/201.600).
- **Audio-Heap-Ereignisse:** keine innerhalb der kontrollierten Audio-Callback-Teilmessungen.
- **Originale Creative-Fidelity inklusive physischer 24-bit-Chorus-Rundung:** nicht abschließend extern gemessen; vorhandener numerischer C01-Vergleich [Draft PR #71](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/71).
- **ASIO/MMCSS in echter Studio-/Audiohardware-Umgebung:** **NOT RUN**. Diese CI-Runner besitzen keine verbindliche physische Audient-/Studio-One-ASIO-Referenz.
- **Kommerzielle Releasefreigabe / Gumroad:** **NO-GO bis Zielrechner-ASIO-/DAW-Stabilitätstest und unabhängiger finales Release-Audit**. Null gemessene CI-Deadlinefehler sind ein starkes Laborresultat, kein universeller Beweis der Echtzeitfähigkeit.

**Produktionscode:** P137 bereits gemergt; hier wird nur die geprüfte Sachlage in der Dokumentation festgehalten. Bitte die Auditbranches P139/P140 nicht in den Produktbranch übernehmen.
