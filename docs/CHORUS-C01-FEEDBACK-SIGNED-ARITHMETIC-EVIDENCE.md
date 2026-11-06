# Chorus C01 – acht EMU8000-Feedback-Modi, numerischer A/B-Vergleich und Hardwarelücke

**Stand:** 6. November 2026. **Separate Chorus-Untersuchung** von der an Codex delegierten **P132-Echtzeitanalyse**. Die Testdateien tragen historische `p132_`-Namen, sind **keine Freigabe oder Änderung des P132-RT-Arbeitsauftrags**.

**Repository:** `challanger2000/125A-AWE-Synthesizer`  
**Ausgangspunkt:** `fix/p122-bank-dirty-audit` Commit `c7d803c1b328166f6f5edcb770aa9c9f8b49ecda`  
**Auditbranch:** `audit/p132-chorus-feedback-evidence-20261106`  
**Numerischer Windows-Lauf:** [#42191668372](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42191668372) **SUCCESS**  
**Funktionaler Fixkandidat:** [Draft PR #67](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/67), **NICHT gemergt**.

## Der entscheidende Hardware-Nachweis fehlt

Die bis jetzt genutzte echte AWE64 Gold CT4390 Aufnahme des [SoundFont Spec Test v3.0](https://github.com/mrbumpy409/SoundFont-Spec-Test) verwendet **Hall 1 / Chorus 1**. Der P97-Renderer programmiert ausdrücklich `Emu8000Fx::kChorusPresets[0]`, dessen Feedbackregister `0xE600` exakt **Feedback 0** bedeutet. Die beiden Verfahren (arithmetisches Signed-Shift und Division gegen Null) sind in diesem Modus bitidentisch. Alle Hardware-P97/P98/P99-Klangvergleichswerte für Chorus 1 sind daher **prinzipiell blind** für den Vorzeichen-Rundungsfehler in Feedbackmodi 1/2/3/4/5/7.

Die originale Linux-EMU8000-Implementierung bestätigt die acht **Registerparameter**, nicht die interne 24-bit-DSP-Rechenregel: https://github.com/torvalds/linux/blob/master/sound/isa/sb/emu8000.c. Das physische Silizium lässt sich nicht aus den Registertabellen ableiten.

## Tatsächlich ausgeführter A/B-Test

In derselben gepinnten Windows-2022-Testumgebung wird **derselbe echte C-Code `emu8k_work_chorus()`** aus `src/engine/snd_emu8k.c` zweimal gebaut. Der erste Lauf verwendet die produktive Originalzeile, der zweite Lauf verwendet in einer **wegwerfbaren CI-Arbeitskopie** exakt die P129-Draft-Kandidatenrechenregel `((int64_t)tap * feedback) / 256`; die Änderung wird per Diff auf genau diese eine Quellcodezeile begrenzt. **Im Git-Entwicklungsbranch und im Auditbranch wird der DSP nicht geändert.**

Der Test setzt pro Modus die tatsächlichen Creative-Parameter (Feedback, Delay, LFO-Depth, Frequenz, rechter Tap), ruft die originale 86Box-Chorusfunktion direkt mit positiven/negativen LSB-Zuständen auf und rendert anschließend **identische vier Sekunden, 44,1 kHz Stereo, 32-bit intern** mit vier bipolar-signierten synthetischen Impulsen. Alle PCM32-Samples werden paarweise verglichen; der zusätzliche PCM16-Gain-Proxy ist **nicht** der komplette VST3-Ausgang (keine Dry/Reverb/EQ-Mischung).

### Windows-Rohvergleich (jeweils 352.800 Stereo-Einzelwerte pro Modus)

| Chorus-Preset | Feedbackbyte | Geänderte interne PCM32-Werte | Maximale Integer-LSB-Differenz | Nachklingen im letzten Sekundenfenster |
| --- | ---: | ---: | ---: | --- |
| 0 – Chorus 1 | 0 | 0 | 0 | Original und Kandidat null |
| 1 – Chorus 2 | 8 | 69.579 | 1 | Original 35.066 Werte ungleich null, Kandidat null |
| 2 – Chorus 3 | 16 | 69.729 | 1 | Original 37.024 Werte ungleich null, Kandidat null |
| 3 – Chorus 4 | 32 | 90.050 | 1 | Original 40.603 Werte ungleich null, Kandidat null |
| 4 – Feedback | 128 | 17.239 | 1 | Original 8.055 Werte ungleich null, Kandidat null |
| 5 – Flanger | 224 | 37.675 | 7 | Original 18.713 Werte ungleich null, Kandidat null |
| 6 – Short Delay | 0 | 0 | 0 | Original und Kandidat null |
| 7 – Short Delay + FB | 192 | 179 | 3 | Original 62 Werte ungleich null, Kandidat null |

**Resultat:** 8/8 vollständige Fälle, sechs rückgekoppelte Modi verändern die interne PCM-Ausgabe, zwei feedbackfreie Modi bleiben exakt bitgleich. Bei initialer -1-LSB-Störung sind alle sechs alten Feedback-Modi nach 32.768 Frames weiterhin negativ statt null; die Kandidatenversion erreicht in allen acht Modi sowohl nach -1 als auch +1 die exakte Null. Für die vier synthetischen Impulse zeigt der Kandidat nach 3–4 s ebenfalls Null, das Original in den Feedback-Modi nicht.

Diese Zahlen beweisen eine **mathematisch konsistente Reparatur der aktuellen Emulation**, aber keine originale Creative-Siliziumquantisierung. Relative RMS-Unterschiede solcher extrem sparsamen Impulse oder Änderungen einzelner interner LSB dürfen **nicht** als allgemeine musikalische Hörschwelle ausgegeben werden.

## Freigabeentscheidung und nächste gezielte physische Probe

**Numerische Choruskorrektur: technisch gestützt; Hardwaregleichheit: NOT RUN; produktive Übernahme: NO-GO.** Ein kompletter Windows-VST3-Regressionslauf des bereits bestehenden älteren Kandidaten aus PR #67 bestand zuvor 41/41 CTests + 47/47 Validator + 3/3 GUI-Smokes. Dieses C01-Audit testet dagegen ausdrücklich nur die isolierte Effektberechnung auf aktuellem P130-Basisstand, also **keine erneute Gesamt-VST3-Regression**.

Für eine Hardwareentscheidung reichen alte Chorus-1-Aufnahmen nicht aus. Erforderlich wären eine originale AWE32/64 mit dokumentierter originaler Creative-Effekt-Presetauswahl, **mindestens die Feedbackmodi 1, 2, 3, 4, 5 und 7** und jeweils identische isolierte impulsartige Anregungen mit nachfolgendem echten digitalen Nullsignal, gleichen Wet-Send- und Master-Einstellungen, 44,1-kHz-PCM via S/PDIF (sofern verfügbar) oder verlustfreiem Audiointerface samt ausgeschalteter automatischer Pegelbearbeitung. Für Vergleichbarkeit wären ein trockenes Kontrollsignal, präzise Tonstartmarkierungen und Metadaten zu ROM, SoundFont, Treiber, Karte, Sampleclock und effect-register/Control-Panel-Modus nötig.

Selbst S/PDIF-Ausgabe kann die interne 24-bit-DSP-Rundung **nicht eindeutig nachweisen**, wenn die beobachtbare 16-bit-Ausgabe die sub-LSB-Differenzen quantisiert. Man kann damit gegebenenfalls **hörbares Tail-/DC-Verhalten** überprüfen, aber nicht ohne Weiteres die interne Bitgenauigkeit beweisen. Bei fehlender Hardwareaufnahme darf das Projekt alternativ eine ausdrücklich als solche dokumentierte **numerische Emulationsnäherung** wählen; diese Entscheidung wird nicht durch grüne Actions vorweggenommen.

**Codex P132 (Realtime) und Chorus C01 sind unabhängig.** Kein DSP-Merge, kein GUI-/ASIO-/Release-GO.
