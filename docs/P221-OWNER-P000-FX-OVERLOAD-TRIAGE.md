# P221 – Befund zum ersten echten Nutzerbank-Audiotest (P000)

**Datum:** 10.11.2026. **Kein Release, keine DSP-Änderung, keine Testschwellen-Abschwächung.**

## Tatsächlich vorliegende lokale Aufnahmen

Der Benutzer hat ausschließlich die private `P000-DRY.wav` und `P220-Recorder-Log.txt` bereitgestellt (weder private SF2, ROM noch fehlerhafte Effekt-WAV wurden im GitHub-Repository veröffentlicht).

Der exportierte Windows-VST3-P220-Recorder protokolliert:

- `P000-DRY program=0 note=48 velocity=64 frames=132300 callbacks=130 rms=0.025650923 peak=0.221374512 private_wav=YES`.
- Die unabhängige WAV-Dateiprüfung bestätigt **44.100 Hz, PCM16 Stereo, 132.300 Frames = 3,0 Sekunden, maximal 0,2213745 = −13,10 dBFS**; die Aufnahme ist hörbar und nicht stumm. Beide Kanäle besitzen Audio.
- Beim nächsten Fall `P000-MODFX` bricht der alte Recorder noch vor dem WAV-Schreiben mit `P220_VST3_FAIL P220 clipping: do not normalize or silently conceal real level errors` ab. Der genaue **Float-Peak, das Sample und die Effekt-/Velocity-Ursache sind aus diesem alten Log nicht bestimmbar**.
- Die erste trockene Aufnahme ist nur eine **tatsächliche VST3-Renderprobe**, kein Beleg für die Übereinstimmung mit einem Original-Creative-Win95-Signal.

## Zusätzlich entdeckter Testkonfigurationsfehler

`tests/p220_77_vst3_pcm_recorder.cpp` hatte für **jede MODFX-Note** die beiden absoluten GUI-Sends `controls[10]=10000` und `controls[11]=10000` gewählt. Nach dem tatsächlich im aktuellen Produkt implementierten P190-Pfad `FxSendLevel::Apply(originalSend,1.0f)` werden damit Reverb und Chorus für alle Stimmen auf **255/255 = vollen Send-Pegel** gesetzt, unabhängig davon, welche SF2/CC-Sends das Original erzeugt hätte.

Der Win95-Creative-Testplan fordert dagegen **CC91=48 und CC93=32**, die bei Originalgenerator-Sends im Creative-Treiber nicht pauschal `255/255` bedeuten. Daher sind diese zwei FX-Signalwege **nicht kontrolliert identisch**. Eine scheinbare Klangabweichung oder Übersteuerung im MODFX-Test könnte auf dieser methodischen Fehlansteuerung beruhen. **Ohne originale Creative- und VST3-FX-Registerwerte, Originalpegel und unverzerrtes Float-Audio ist keine definitive Fehlerursache zulässig.** Auch für DRY muss unabhängig geprüft werden, ob originalseitige SF2-Sends trotz CC91/93=0 weiter aktiv sind, während der P190-GUI-Knopf sie im VST3 absolut abschaltet.

## Korrekte P221-Diagnose, keine Fehlerunterdrückung

Der isolierte Recorder wurde **ausschließlich im Testcode** erweitert:

1. Er misst je Fall unveränderte VST3-`float`-Samples vor einer 16-Bit-Konvertierung und protokolliert **Maximum, RMS, Anzahl Übersteuerungs-Samples, erstes Frame, Kanal und den ursprünglichen Wert**.
2. Bei Clipping oder Stille wird ausdrücklich **kein gültiges P220-PCM16-Audio als PASS** gespeichert. Stattdessen entsteht eine zusätzliche private **32-Bit-IEEE-Float-WAV** `*-FAILED-UNCLIPPED-F32.wav`, die Floatwerte **auch oberhalb von ±1.0 unnormalisiert** erhält.
3. Eine einzelne ungültige MODFX-Note soll die Untersuchung der anderen Programme nicht mehr sofort beenden; der gesamte Lauf bleibt dennoch mit **Exitcode != 0** und einem Fehlerzähler `FAIL`/Release-`BLOCKED`.
4. Ein eigenständiger Modus `owner-p000-diagnostic` analysiert nur die ersten beiden Originalbank-Szenarien (Dry und Wet), ohne vorzutäuschen, die übrigen 76 Programme geprüft zu haben. `tools/P221-LOCAL-P000-CLIP-DIAG.bat` erzeugt private, jeweils getrennte Diagnoseläufe und überschreibt keine alte Aufnahme.

## Verbindliche weitere Abnahme

Vor einem zulässigen Original-Creative-Klangvergleich müssen **tatsächliche Effektregister und Effektprogrammierung** zwischen Original-Win95/86Box und VST3 für die betreffenden MIDI-Events nachweislich auf gleiche Ansteuerung gebracht werden; ein bloßer Knopfwinkel oder die Verwendung derselben CC-Werte genügt nicht. Danach müssen die ursprünglichen 77 Presets (154 Fälle) sowie Amplitudenhüllkurven, Filter, Effekte, Loops, Sample-Mapping, Velocity, Recall usw. verglichen werden. P220 bleibt **0/77 PASS, ursprüngliche Creative-Aufnahmen fehlen: BLOCKED**. Hier wurde keine private ROM/SF2-Datei veröffentlicht und **kein produktiver Synth-DSP geändert**.

Der P221-Code ist ein **Forschungs-/Korrekturkandidat**. Der Windows-Build und die synthetische PCM-Kontrolle des neuen Diagnosepfades müssen separat erfolgreich sein, bevor das neue Paket als getestet bezeichnet werden darf.
