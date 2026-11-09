# P210 – 14-Preset EG1-Generator-Sweep am originalen Creative-Windows-95-Treiber

**Ziel:** Die ausschließlich für eine einzelne Note plausiblen P208-Formeln für `holdModEnv` (Zeitcent über 725-µs-Ticks und danach 92-ms-Trunkierung) und `sustainModEnv` (ganzzahliger Prozentsatz) gegen **14 unterschiedliche tatsächlich vom originalen SBAWE.VXD verarbeitete synthetische SoundFont-Presets** testen, nicht erneut eine Klangkurve anpassen.

Die Testbank wird reproduzierbar aus einer eigenen 440-Hz-Sinusprobe erstellt. Alle 14 Programme verwenden denselben Sample und dieselben Parameter für `delayModEnv=0`, `attackModEnv=0`, `modEnvToPitch=1200`, `decayModEnv=0`, MIDI-Note59 bei Velocity100. Variiert werden ausschließlich **holdModEnv** (−12000, −2400, −1200, −600, 0, 600, 1200, 2400 Timecents) und **sustainModEnv** (0, 250, 499, 500, 501, 750, 1000 Einheiten) mit derselben jeweils unveränderten Gegenachse.

**Originaltreiber:** Die originale Creative-Win95-WinMM-Software läuft auf einer emulierten AWE64 Gold in 86Box. Der neue Forschungsadapter `--p210-sweep` erfasst für jedes Programm die tatsächlichen EMU8000-Port-Writes in einer eigenen begrenzten Note-on/off-Periode und verifiziert die von der Originalsoftware gelieferten MIDI-Meldungen. Kein Host-MIDI-Renderer ersetzt den Originaltreiber.

**Native Gegenseite:** Derselbe generierte SF2 wird ohne Änderungen an den Audiosamples mit der alten und der P208-hypothetischen 125A-SF2-Konvertierung durch die echte native 86Box-Chipkomponente gespielt. Mehrere echte Port-Writes je Register und aktives Voice-Mapping werden mit dem bereits adversarial geprüften P89-Parser verglichen. Die Vergleichsdaten enthalten nur numerische Registerwerte; Original-SF2, ROM, Windows-Datenträger und raw Port-Trace werden nie als Artifact veröffentlicht.

**Wichtig:** Wenn der Originaltreiber andere Werte liefert als die Hypothese, ist das ein **falsifizierendes Forschungsergebnis**, kein Grund, den Test auf Grün zu trimmen. Jede Registerhypothese bleibt zunächst nicht-produktiv. Selbst 14/14 Gleichheit schließt nur diesen getesteten SF2-Parameterbereich, nicht die gesamte AWE-Emulation und insbesondere nicht die rund 82 Cent Abweichung der physischen CT4390-Attack.

**Produktiver VST3 bleibt unverändert.** Resultate und Originaltreiber-Lauf werden erst nach dem tatsächlichen Actions-Test samt Evidenz dokumentiert.
