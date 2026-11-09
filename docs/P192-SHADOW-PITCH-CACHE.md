# P192 – DSP-neutrale Shadow-Pitch-Math-Optimierung

Vom Produktstand \`bc565cfc238ece6f59af6ef6e7cc950136688b8d\` isolierter Branch \`perf/p192-shadow-pitch-cache\`.

ETW aus \`#42571191825\` hat ein On-CPU-Laufzeitproblem im zweiten Callback bei 128 Frames/30 Stimmen/Filterautomation nachgewiesen. Nachträglich dekodierte ETW-Images und StackWalk zeigen wiederholte UCRT-Mathematikaufrufe sowohl aus der 86Box-EMU8000-Verarbeitung als auch aus dem *weggeworfenen* schattenseitigen Register-Renderer. Die echten 86Box-Stimmen, ihr SVF/Interpolations-DSP, Filterkoeffizienten und die Creative-Effektprogramme bleiben deshalb **unverändert**.

Der P192-Experimentalkandidat merkt sich pro Shadow-Stimme das **bitidentische doppelt genaue Pitch-Eingangsargument** und den exakten vorherigen \`std::pow\`-Rückgabewert. Nur bei **exakt gleichem \`double\`** wird die neuerliche UCRT-Berechnung übersprungen; bei jeglichem anderen Pitch wird unverändert die bisherige Gleichung ausgewertet. Die Option \`AWE125_TEST_DISABLE_MIRROR_PITCH_CACHE\` erzwingt den ungeänderten Originalpfad für eine unabhängige Vergleichsversion **auf demselben Windows-Runner**.

Die eigens dafür erzeugte 30-Stimmen-Synthese mit synthetischem Zero-ROM/Filter-SF2 liefert PCM plus 32-Voice-Register-Snapshot. Fünf Raten-/Blockgrößen-/Polyphonie-Fälle müssen bitidentisch sein, während ABBA-Wiederholungen der 128/30-Matrix die reale CPU-Änderung *unter identischem Testsystem* messen. **Teststatus noch ausstehend.** Ein geschätzter Geschwindigkeitsschub ist kein Freigabenachweis. Erst bei verifiziertem messbarem Vorteil, PCM-/Register-Gleichheit und anschließend vollständigem Windows-VST3-Validator/Test Lab darf der Patch in den P190-Produktbranch übertragen werden. Bis dahin bleibt er getrennt, **Release NO-GO**.
