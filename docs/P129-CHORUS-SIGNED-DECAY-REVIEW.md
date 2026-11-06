# P129 – Chorus-Feedback, deterministische Signed-Quantisierung (noch keine Hardware-Abnahme)

**Basis:** P128 mit zusammengeführten Master-/GUI- und MIDI-Programmkorrekturen, Commit `ac2cab282b2c1ed89dc9aee82feb4364c6e810c1`.

## Reproduzierter Fehler

Die originale EMU8000-Chorus-Nachbildung speichert bei dauerhaftem Null-Eingang und negativer kleiner Rückkopplung einen von der Rundungsrichtung abhängigen, dauerhaften Integer-Rest:

`buffer[write] = input + ((tap * feedback) >> 8)`

Ein arithmetischer Shift von `-1 * feedback` mit `feedback=1..255` ergibt unter Windows MSVC `-1` statt `0`; nach dem Abklingen bleibt der Ringpuffer im nichtverschwindenden Zustand. Bei positiven `+1`-Werten oder `feedback=0` verstummt er dagegen.

- Reproduktion am wirklichen 86Box-Chipkern unter Windows: [#42166092101](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42166092101), Presets 1/2/3/4/5/7 FAIL, 0/6 PASS.
- Isolierter Kandidat: [#42166164529](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42166164529), nach 32768 Samples mit Null-Eingang alle 8 Presets aus beiden Vorzeichen exakt null, 16/16 PASS.
- Direkter A/B-PCM-Vergleich Original/korrigiert [#42169168137](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42169168137): beide Presets ohne Feedback **bitgenau unverändert**. Die sechs Feedback-Presets zeigen Änderungen von maximal 1/1/1/1/7/3 32-bit-Integer-LSB im Anregungsfenster. RMS-Abweichung relativ zum Ausgangssignal zwischen −52,69 und −68,41 dB; im letzten Sekundenfenster bleibt original 1–7 LSB stehen, korrigiert null. Siehe Roh-PCM und metrics.csv in den Actions-Artefakten.

## P129-Änderung

Bei gleicher Effektstruktur wird allein die Rückkopplungsmultiplikation in **signed 64-bit** berechnet und durch **ganzzahlige Division durch 256** (truncation toward zero) zurückskaliert. Damit entfallen der dauerhaft negative Rundungsfehler und ein mögliches 32-bit-Multiplikationsüberlaufproblem. Keine Schwellenwerte, kein Stummschaltungsfilter und keine neue dynamische Speicherzuweisung.

Der direkte Chipregressionstest `125A_p129_chorus_signed_decay` ist dauerhaft in die Engine-CTest-Suite eingebunden. Die vollständige Windows-Abnahme auf dem *kombinierten P128+P129-Branch* erfolgt über `.github/workflows/p129-chorus-full-windows.yml`.

## Wichtige Freigabegrenzen

**Die Hardwaregleichheit des Rundungsverhaltens ist nicht belegt.** Der ursprüngliche EMU8000-Effektprozessor ist ein proprietärer DSP. Das A/B-Protokoll belegt nur die Änderungen gegenüber der bisherigen Emulation, nicht die Richtigkeit gegenüber einer physischen AWE32/AWE64. Diese Änderung bleibt als Reviewkandidat im separaten PR, bis entweder eine gleich eingestellte AWE-Hardwareaufnahme den Rundungsverlauf bestätigt oder der Nutzer die ausdrücklich nicht bitgenaue Näherung akzeptiert.

**Auch mit bestandener Windows-Regression gilt: RELEASE-NO-GO**, solange ASIO/DAW-Deadline-Tests und der unabhängige Gesamtaudit fehlen. Nicht den Status der früheren offenen Fehler schönrechnen.
