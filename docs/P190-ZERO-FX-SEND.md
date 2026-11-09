# P190 – Chorus/Reverb bei 0 % wirklich trocken (Bass-Mono)
Stand: 2026-11-09 · Entwicklungsbranch `fix/p190-zero-fx-dry`

## Nutzerbefund und nachgewiesener Implementierungsfehler

Ein ursprünglich mono abgemischter SF2-Bass klingt bei den angezeigten
Chorus-/Reverb-Reglerständen 0 ungewollt räumlich. Das entspricht
nicht dem erwarteten 125A-Bedienvertrag **0 % = AUS**.

Die tatsächliche VST3-Implementierung in
`Synth::StartLayers` addierte vorher einen positiven GUI-Betrag zum
vorhandenen SoundFont-Preset- und MIDI-Send. **Bei 0 % wurde nur keine
Zugabe vorgenommen**, aber die in `SF2` (Generatoren 15/16) oder durch
CC91/93 gespeicherten Send-Pegel blieben erhalten.
Darüber hinaus sind die echten Creative-Effektpreset-Indices 0..7
verschiedene **Effektarten**: `Chorus Type=0` ist `Chorus 1`,
`Reverb Type=0` ist `Room 1`, nicht AUS.

Der eigentliche ROM-pflichtige Produktionspfad benutzt
`Emu8000Core::Chip::Box86`. Er rendert eigene Effekte; Änderungen an
`Emu8000Fx`-Float-Workalikes würden das eigentliche Problem nicht
beheben. Hier muss der EMU8000-Register-Send selbst auf null gesetzt
werden: `PTRX[15:8]` für Hall und `CSL[31:24]` für Chorus.

## Entwicklungsfix

- Beide GUI-Controls 10/11 werden zu **absoluten Send-Level-Reglern**
  mit monotonem Verlauf. `0` schreibt den Send-Wert `0`, selbst wenn
  das Patch und MIDI einen größeren Wert verlangen; `100` erreicht
  `255`, Zwischenwerte berücksichtigen den originalen Patch/MIDI-Pegel.
- Per Voice wird der noch unbearbeitete Patch/MIDI-Send archiviert.
  So können Änderungen an den Reglern bei aktuell gehaltenen Tönen
  direkt die tatsächlichen Hardware-Register überschreiben.
- Unabhängige Register-/Matheregressionsprüfungen, echte 86Box-
  Stereo-PCM-Prüfung mit synthetischer SoundFont und absichtlich
  hohen originalen Effekt-Sends.
- Keine Veränderung der acht Creative-Effektarten/-Registernamen,
  des Filters, des Panorama- oder sonstiger DSP-Parameter.

## Verbindliche Abnahme und Grenzen

Die Änderung ist **bewusst anders als die V11-SoundFont-Neutralstellung**.
Vor einem Merge/Release sind eine explizite V11-Projektmigrationsstrategie
und Legacy-Recall-/Save-/Automationtests erforderlich; alte Projekte
dürfen nicht stillschweigend anders klingen. P190 ist daher zunächst
nur ein **nicht freigegebener Fix-Kandidat**.

Alle produktiven Windows-VST3-Builds müssen die gesamte CTest-Suite
inklusive 125A_p190_fx_zero_dry, den VST3-Validator, 3 EditorHost-
Smokes und das universelle Test Lab bestehen. Echte PCM-Behauptungen
müssen durch binäre L/R-Werte sowie send-register-oracle gedeckt sein.
Ein Test mit Nutzer-ROM, -SF2 und DAW bleibt NOT_RUN, wenn entsprechende
Dateien nicht vorliegen. P184/P189-ASIO-NO-GO bleibt bestehen.

**Keine VST3-Verkaufsfreigabe und kein FULL AUDIT aufgrund eines grünen
Entwicklungsbuilds.**

## P190 Windows-Gesamtabnahme und Klangtreue: nachgetragene Quellenkontrolle (09.11.2026)

[Windows-Gesamtlauf #42550765204](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42550765204) wurde mit Quellstand f4e2624a3c6207f3f10aca255b067589b2c18efa erfolgreich abgeschlossen:
- 67/67 CTests inklusive P190 FX-Send und korrigierter P171-Held-Note-Regression;
- 537/537 Steinberg VST3-Validatorprüfungen am tatsächlichen Modul;
- 3 EditorHost-Smokes und 99 tatsächliche GUI-Interaktionen;
- unabhängiges universelles 125A Test Lab TECHNICAL_PASS;
- 0/14.400 Callback-Deadlineüberschreitungen in der gemessenen künstlichen CI-Matrix.
Die frühere P190-PCM-Gegenprobe zeigte eine normierte L/R-Effektivwertdifferenz von 0,000365 bei Dry und 0,096809 bei maximalen Effekten. Alle Nachweise beziehen sich auf synthetische Testdaten. NO-GO für Release, kein privater Original-ROM-/SF2-/DAW-/ASIO-Test.

### Releaseblocker: alte V8–V11-Projekte dürfen nicht stillschweigend anders klingen

Alte gespeicherte GUI-Send-Parameter 10/11 hatten die Bedeutung 0 = kein zusätzlicher Boost, aber SF2-/CC91-/CC93-Effekt-Sends blieben erhalten. P190 definiert dagegen 0 = absolut trocken. Ein unverändert geladener alter Wert 0 klingt nun anders. Alte Sends trotz sichtbarer Reglerstellung 0 weiterzugeben, wäre mit der ausdrücklichen Nutzervorgabe unvereinbar.

Vor der Releasefreigabe ist eine ausdrücklich definierte V12-Migration mit sichtbar **nichtnulligen** effektiven Reglerwerten für alte wet-Projekte zu validieren. Eine feste Umrechnung der alten Reglerwerte mit der heutigen P190-Send-Kurve kann je nach SF2-/CC-Basis unterschiedlich klingen. Außerdem speichert der VST3-Host automatisierte alte Parameterwerte unabhängig vom Plugin-State: eine Plugin-interne State-Migration allein kann alte Host-Automation NICHT sicher konvertieren.

Pflichtnachweise: V1/V7/V8/V9/V10/V11-Projekte mit trockenem und nassem SF2-/CC-Send, Erstnote, gehaltene und ausgelassene Stimmen, Controller-/Prozessor-Recall, Save/Reopen, alte Host-Automation, Zero-/Mid-/Max-Reglerwerte sowie fehlende Assets. Eine bei Live-Reglerwechsel 100 -> 0 eventuell weiterklingende alte Hall-/Chorus-Fahne ist separat zu falsifizieren: null neue Send-Register beweisen nicht, dass die alten Delay-Tails sofort vollständig stumm werden.

**Bis zur vollständigen Abnahme: keine V12-Umsetzung auf Verdacht, kein Main-Merge, kein Verkauf.**

### EMU8000 Fidelity: externe Empfehlungen gegen produktiven Code geprüft

- src/engine/Synth.cpp nutzt für den historisch transkribierten Velocity-Cutoff je nach Treiber die Untergrenze 0x46 = 70, während [SoundFont-Spec-Test](https://github.com/mrbumpy409/SoundFont-Spec-Test) AWE-Verhalten ungefähr ab Velocity 64 beschreibt. Die dortige v3.0-Referenz prüft Werte 127/111/95/79/63/47/31/15 und kann **64 von 70 nicht unterscheiden**. Vor einer Änderung zusätzliche Velocities 63,64,65,69,70,71 und nachvollziehbare Register-/Spektralmessungen durchführen.
- src/engine/snd_emu8k.c wählt standardmäßig vierpunktige kubische B-Spline-Interpolation (RESAMPLER_BSPLINE4), nicht lineare Interpolation. Filter und Effekte enthalten empirisch gefittete Modellanteile, sind keine bewiesen bitexakten internen Hardware-Algorithmen.
- src/engine/Emu8000.cpp rendert das Chipmodell weiterhin auf dem nativen 44,1-kHz-Takt und resampelt erst für abweichende Host-Sampleraten. Eine pauschale Behauptung falsch laufender Hüllkurven/LFOs bei 48/96 kHz passt daher nicht zum vorhandenen Signalpfad.
- Die echte AWE64-Gold-CT4390-Aufnahme ist bereits in docs/P97-AWE64-GOLD-AUDIO-COMPARISON.md untersucht. Gesamtvergleich: Envelope-Korrelation 0,95155, Wellenformkorrelation 0,01049 und relevante frequenzabhängige Abweichungen. Ein identisches Ergebnis von Plugin und 86Box beweist lediglich Port-/Emulationsgleichheit, keine Hardware-Parität. Einen globalen EQ nicht ohne kausalen trockenen Referenzvergleich ergänzen.

**Quellenbewertung:** eigener produktiver Quellcode + P97-Evidenz; historische Hardware-Details ggf. durch unabhängige Referenzfenster bestätigen. Kein unnötiger Hardwarekauf.

## P190 next candidate: existing reverb/chorus tail return bypass (PENDING NEW CI)

The earlier gate proved new voice sends become zero but not that previously excited delay/reverb feedback stops reaching the mixer. This candidate adds per-instance, runtime-only 125A return masks to the actual Box86 chip (not its unused float DSP), without rewriting the original Creative effect preset tables. The effect algorithm continues to run so its internal timebase stays coherent. The VST3 Processor integration CTest compares three wet-to-zero scenarios against an independently started always-dry PCM clone after the 980-frame chip FIFO latency. The local 125A adapter header shadows the upstream original unchanged. Any precomputed wet FIFO samples may remain audible until the declared chip latency passes; instantaneous muting at host event offset is not claimed. Release and migration remain NO-GO until run evidence.

### Nachprobe der unabhängigen P27-PCM-Prüfung

Der erste Windows-Lauf nach Einbau des Return-Bypasses kompiliert, aber CTest 50 (SF2 Audio Integration) schlägt in zwei P27-Wet-Vergleichen fehl: Der synthetische Test schrieb positive CSL/PTRX-Sends DIREKT in den Chip, ließ aber die neuen Benutzer-FX-Regler auf 0% und forderte damit gleichzeitig einen stummen Effekt-Rückweg. Der ursprüngliche Test prüfte Wet-Sends, nicht die neue GUI-Bedienregel. Die P27-Fixture aktiviert nun VOR der Registermanipulation den zugehörigen GUI-Send-Regler (1.0 = wet); bei `0` bleibt die separate P190-Trockenprüfung verantwortlich. Diese Änderung ist ausdrücklich eine Reparatur der Test-Vorbedingung und kein Abschwächen eines kritischen Audioasserts: Wet-Chorus und Wet-Reverb müssen weiterhin nachweisbar anderen PCM erzeugen als Dry.
