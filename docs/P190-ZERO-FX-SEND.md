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

Die Änderung ist **bewusst anders als die interne V11-SoundFont-Neutralstellung**. Es gibt aber keine veröffentlichte Vorgängerversion dieses 125A-Plugins und keine bekannte Bestandsinstallation, deren Altprojektklang ein Produktversprechen wäre. Darum gibt es **keinen Legacy-FX-Betriebsmodus**. Das interne State-Format bleibt mit vorhandenen V1–V11-Feldern lesbar, aber bei Chorus/Reverb 0% gilt für alle geladenen Daten derselbe absolute Trockenvertrag. P190 bleibt bis zur produktiven Abnahme ein **nicht freigegebener Fix-Kandidat**.

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

### Entscheidung: keine historische Legacy-Effektlogik nötig

Die früher diskutierte automatische V12-Migration war eine Fehlpriorisierung: Das 125A-AWE-Plugin besitzt **keinen veröffentlichten Vorgänger**. Nutzerziel ist ohne Ausnahme **0% = trocken**. Deshalb keine zusätzliche Legacy-Engine, kein Legacy-FX-Modus und keine neuen VST3-Parameter oder Versionssprünge zur Simulation von zuvor unveröffentlichten Entwicklungszuständen.

Die alte V1–V11-State-Struktur wird zwar weiterhin eingelesen, aber die Effektregler werden bewusst als absolute P190-Pegel behandelt. Das ist eine dokumentierte Verhaltenskorrektur des unveröffentlichten Plugins, keine zugesicherte historische Audioidentität. Die allgemeinen Regressionen für State-Parsing, Recall, Save, Host-Automation sowie 100% -> 0% und noch aktive Effektfahnen bleiben verbindlich; eine künstliche **Legacy-Wet-Emulation** ist ausdrücklich ausgeschlossen.

P191 wurde nur als nicht freigegebener Zwischenversuch auf dem Entwicklungsbranch erstellt und danach vollständig aus dem Produktbaum zurückgenommen. Keine Änderungen an Main. Die realen DAW-/ASIO- und Original-AWE64-Klangtests sind weiterhin nicht erledigt, also bleibt die **Releasefreigabe NO-GO**.

### EMU8000 Fidelity: externe Empfehlungen gegen produktiven Code geprüft

- src/engine/Synth.cpp nutzt für den historisch transkribierten Velocity-Cutoff je nach Treiber die Untergrenze 0x46 = 70, während [SoundFont-Spec-Test](https://github.com/mrbumpy409/SoundFont-Spec-Test) AWE-Verhalten ungefähr ab Velocity 64 beschreibt. Die dortige v3.0-Referenz prüft Werte 127/111/95/79/63/47/31/15 und kann **64 von 70 nicht unterscheiden**. Vor einer Änderung zusätzliche Velocities 63,64,65,69,70,71 und nachvollziehbare Register-/Spektralmessungen durchführen.
- src/engine/snd_emu8k.c wählt standardmäßig vierpunktige kubische B-Spline-Interpolation (RESAMPLER_BSPLINE4), nicht lineare Interpolation. Filter und Effekte enthalten empirisch gefittete Modellanteile, sind keine bewiesen bitexakten internen Hardware-Algorithmen.
- src/engine/Emu8000.cpp rendert das Chipmodell weiterhin auf dem nativen 44,1-kHz-Takt und resampelt erst für abweichende Host-Sampleraten. Eine pauschale Behauptung falsch laufender Hüllkurven/LFOs bei 48/96 kHz passt daher nicht zum vorhandenen Signalpfad.
- Die echte AWE64-Gold-CT4390-Aufnahme ist bereits in docs/P97-AWE64-GOLD-AUDIO-COMPARISON.md untersucht. Gesamtvergleich: Envelope-Korrelation 0,95155, Wellenformkorrelation 0,01049 und relevante frequenzabhängige Abweichungen. Ein identisches Ergebnis von Plugin und 86Box beweist lediglich Port-/Emulationsgleichheit, keine Hardware-Parität. Einen globalen EQ nicht ohne kausalen trockenen Referenzvergleich ergänzen.

**Quellenbewertung:** eigener produktiver Quellcode + P97-Evidenz; historische Hardware-Details ggf. durch unabhängige Referenzfenster bestätigen. Kein unnötiger Hardwarekauf.

## P190 Rückweg-Abschaltung alter Chorus-/Reverb-Fahnen (Windows-geprüft)

The earlier gate proved new voice sends become zero but not that previously excited delay/reverb feedback stops reaching the mixer. The subsequent Windows run #42556095257 has now passed this additional PCM condition. This candidate adds per-instance, runtime-only 125A return masks to the actual Box86 chip (not its unused float DSP), without rewriting the original Creative effect preset tables. The effect algorithm continues to run so its internal timebase stays coherent. The VST3 Processor integration CTest compares three wet-to-zero scenarios against an independently started always-dry PCM clone after the 980-frame chip FIFO latency. The local 125A adapter header shadows the upstream original unchanged. Any precomputed wet FIFO samples may remain audible until the declared chip latency passes; instantaneous muting at host event offset is not claimed. The run evidence is PASS for technical Windows regression; release remains NO-GO for other real-world acceptance criteria.

### Nachprobe der unabhängigen P27-PCM-Prüfung

Der erste Windows-Lauf nach Einbau des Return-Bypasses kompiliert, aber CTest 50 (SF2 Audio Integration) schlägt in zwei P27-Wet-Vergleichen fehl: Der synthetische Test schrieb positive CSL/PTRX-Sends DIREKT in den Chip, ließ aber die neuen Benutzer-FX-Regler auf 0% und forderte damit gleichzeitig einen stummen Effekt-Rückweg. Der ursprüngliche Test prüfte Wet-Sends, nicht die neue GUI-Bedienregel. Die P27-Fixture aktiviert nun VOR der Registermanipulation den zugehörigen GUI-Send-Regler (1.0 = wet); bei `0` bleibt die separate P190-Trockenprüfung verantwortlich. Diese Änderung ist ausdrücklich eine Reparatur der Test-Vorbedingung und kein Abschwächen eines kritischen Audioasserts: Wet-Chorus und Wet-Reverb müssen weiterhin nachweisbar anderen PCM erzeugen als Dry.

## Verifizierte Windows-Gesamtprüfung der Rückweg-Korrektur

**Geprüfter Quellstand:** `09e5ac7a9b99e5e4fd1c346f8161339fe74b4e53`. [P190 Windows-Actions #42556095257](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42556095257) **SUCCESS**:

- **67/67 CTests**, einschließlich P190-Held-Note/Feedback-Tail-PCM-Gegenprobe mit drei Varianten (nur Reverb, nur Chorus, beide) und unabhängiger dauerhaft trockener Vergleichsinstanz nach 980-Frame-FIFO. Alle drei Fälle bestanden. Die separate ursprüngliche P27-Wet-Registerprobe weist weiterhin hörbar verändertes PCM nach, nachdem der GUI-Effektpfad ausdrücklich auf WET gesetzt wurde.
- **537/537 Steinberg-VST3-Modulvalidator**; **3 GUI-Quick-Smokes** und **99/99 physische VSTGUI-Interaktionen**; **universelles Test Lab TECHNICAL_PASS**, dessen technische Statusdatei `release_approved=false` meldet.
- **0/14.400** gemeldete Callback-Deadlinemisses in dieser künstlichen Windows-CI-Matrix, kein physischer ASIO-/MMCSS-Betrieb.
- Artefakte: `P190-FX-Zero-Dry-Windows-x64-VST3-TEST-A` (GitHub Artifact ID 13648226418; Development-Preview, **kein Verkauf/Release**) und `P190-FX-Zero-Dry-Full-Regression-A` (Artifact ID 13648087065; 315,6 MB).

**Reichweitengrenzen:** Der echte proprietäre User-ROM/SF2-Klang wurde nicht erneut auf dem Runner geprüft; die Studio-One-/Fender-Studio-Pro-Abnahme bleibt NOT RUN, ebenso vollständige reale AWE64-Parität. Für eine ganz unmittelbar nach der Steuerungsänderung bereits vorgerechnete Audioausgabe können bis zu 980 native Frames im Chip-FIFO verbleiben. Ein garantiert sample-sofortiger Wet-Stopp wird nicht behauptet. Die frühere Legacy-Migrationsanforderung wurde zurückgenommen, weil es keine öffentlich ausgelieferte Vorgängerversion gibt. Ausschließlich absolute P190-Effektpegel bleiben vorgesehen. **RELEASE NO-GO** wegen weiter fehlender realer Klang-/DAW-/ASIO-Abnahme; Main unverändert.

## P191-Rücknahme / Versionsentscheidung

Rücknahmebasis des Produktionsbaums: vollständig geprüfter P190-Commit `09e5ac7a9b99e5e4fd1c346f8161339fe74b4e53` mit nachfolgender Dokumentation `2f3210e0f2fd0829b1addff1dc73a7f5c755f292`. Die beiden experimentellen P191-Commits werden in einem vorwärts gerichteten Revert ersetzt; im resultierenden Baum gibt es keinen V12-Modus, keinen Parameter 1202 und keine `ApplyLegacy`-Funktion. Die neue CI prüft exakt den wiederhergestellten P190-Produktbaum und die hier korrigierten Dokumente. Die alleinige alte Issue #93 ist kein Releaseblocker mehr.

## P190 Realtime-Audit: CI PASS trotz RT-FAIL verhindert (09.11.2026)

Auf dem **unveränderten P190-Produktcode** meldete [Windows #42567484894](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42567484894) **67/67 CTests**, **537/537 VST3-Validator**, **99/99 GUI-Interaktionen** und **Test Lab TECHNICAL_PASS**, aber auch **25/14.400 Deadlineüberschreitungen** in der synthetischen 72-Zellen-Callback-Matrix. Die bisherige CI hatte trotzdem erfolgreich abgeschlossen; das war **ein QA-Fehler in der Freigabegeste**, keine Klang-/Funktionstest-Niederlage. **Echtzeitverdict: FAIL / Ursache unbestimmt.** Die ETW-Aufzeichnung dieser konkreten Ausreißer ist nicht nachgewiesen; Schedulerpreemption darf nicht aus früheren unabhängigen Ausreißern herüberinterpretiert werden.

In P190 folgt nun nach **beiden Artefakt-Uploads** ein strikt prüfender `tools/p190_rt_deadline_gate.py`: 72×200 vollständige Matrixelemente, Summen, Source-SHA und NO-GO-Provenienz müssen vorhanden und konsistent sein. **Schon 1/14.400 Überschreitungen führt zum roten GitHub-Run**, vollständige Rohdaten bleiben als Artefakt erhalten. Bei 0/14.400 heißt der Status ausdrücklich `PASS_LAB_ONLY`, niemals reale Hardware-/ASIO-Freigabe. Die eigene Positiv-/Negativkontrolle des Gates prüft 0 und 25 misses sowie verfälschte und abgeschnittene Matrizen. Die Entscheidung verbessert die Abnahmeehrlichkeit; sie behebt keine tatsächlich gemessene Callbackzeit.

## P192 – auf P190 angewendete Realtime-Optimierung

[Isolierter Same-Runner-ABBA Windows-Nachweis #42578406545](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42578406545): der C++-Schattenrenderer überspringt `std::pow(2,pitch)` nur bei EXAKT identischem `double`-Pitch-Eingang derselben Stimme. Es gibt keine Quantisierung, geänderte Filterkoeffizienten oder Änderungen am tatsächlich hörbaren 86Box-Renderer. Ein testbares Compile-Flag `AWE125_TEST_DISABLE_MIRROR_PITCH_CACHE` lässt den ursprünglichen Original-Rechenweg unverändert laufen.

**Fünf verifizierte Mono-/Polyphonie-/Sampleraten-A/B-Paare (1/16/30 Stimmen; 44,1/48/96 kHz) lieferten bitidentische RAW-PCM-Dateien UND bitidentische Voice-/Chipregister.** Bei 128 Frames und 30 Stimmen betrug der Median 770,0 µs (ungecacht) zu 685,6 µs (Cache), also ca. 10,96 % weniger. Ein ABBA-Repetitionslauf auf demselben Windows-Runner bestätigte das mit Medianratio 0,8908. Diese Zeiten stammen **ausschließlich aus dem isolierten Core-RenderBench**, nicht dem exportierten VST3-Prozessor. Die kommerzielle/ASIO/DAW-Releasefreigabe bleibt NO-GO.

Der Patch ist deshalb in den P190-Produktbranch übernommen, aber eine **vollständige neue P190-VST3-/Validator-/GUI-/Test-Lab-/RT-Abnahme des gepinnten neuen Commit-SHAs ist Pflicht**, bevor daraus auch nur ein Windows-Labor-Echtzeitverdict abgeleitet werden darf. Einzelne virtuelle Runner-Ausreißer werden nicht nachträglich ignoriert oder aus Daten herausgefiltert.

## P192 – gesamter Windows-P190-VST3-Produktbuild nach Optimierung PASS (09.11.2026)

**Gepinnter Produkt-Quellstand:** `650a2c8408b7e068b84fd8a5d202e21dcaf17330`. [Windows-Gesamtlauf #42578678687](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42578678687) **SUCCESS**, explizite Quell-SHA/Modul-Provenienz. Die produktive AWE64-EMU-Klangerzeugung/FILTER/Chorus/Reverb/ROM-Mappings ist unveraendert; P192 cached nur eine exakt identische Doppelgenauigkeits-Pitch-Potenz im ausgangsseitig nicht benutzten Shadow-Renderer.

- **67/67 CTests bestanden**, einschliesslich echter PCM-Pruefungen, Nullpunkt-/Wet-Tail-/Filter- und Baseline-/Gegenmutationspruefungen.
- **537/537 Steinberg-VST3-Validatorpruefungen** am exportierten x64-VST3.
- **99/99 GUI-Interaktionen** mit Original-Faceplate, 3 EditorHost-Quick-Smokes.
- **Universelles 125A Test Lab: TECHNICAL_PASS**, Release-Flag dort ausdrücklich false.
- **Echtzeitmessmatrix: 0/14.400 Deadlineueberschreitungen** in diesem Windows-2022-GitHub-Runner; die unveraenderte strenge Negativkontrolle des RT-Gates (0, 25, manipulierte / unvollstaendige Zellen) bestand, Endurteil **`PASS_LAB_ONLY`**.
- **Windows-Entwicklungsbuild (kein Release):** GitHub-Actions-Artefakt `P190-FX-Zero-Dry-Windows-x64-VST3-TEST-A`, ID **13656691885**; vollstaendige Regressionen `P190-FX-Zero-Dry-Full-Regression-A`, ID **13656722011**.

**Gegenproben:** Isoliertes P192-Same-Runner-ABBA [#42578406545](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42578406545), 5 PCM-/Chip-Register-Bitidentitaeten; in 128-Frame-/30-Voice-Renderengine 770,0 -> 685,6 µs Median (~11 %). Vorheriger P190-Run #42571191825 hatte beim alten Code 1/14.400 echten verifizierten Miss. Die separat echte ETW-Untersuchung war nicht als reiner Schedulerfehler erklaerbar; eine einzige aktuelle Null-Fehler-Matrix beweist keine universelle Ausreisserfreiheit.

**Freigabestatus:** Windows-Labortests PASS, reale proprietaere 125A ROM-/77-SF2-Medien im kommerziellen Host, physische DAW-/ASIO-Bedingungen und finale Hardware-Klangparitaet **NOT RUN**. **Kein FULL AUDIT / keine kommerzielle Releasefreigabe / kein Merge nach main.**
