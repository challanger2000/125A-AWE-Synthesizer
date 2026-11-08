# P170/P171 — Funktionskorrekturen und falsifizierbare Audioprüfung

Stand 2026-11-08. Branch `fix/p170-p171-audio-corrections`.
**Entwicklungsprüfung; kein FULL AUDIT, kein Release, kein Merge.**
Windows-Nachweise des neuen Stands werden nach Abschluss der beiden vollständigen
Windows-Jobs unten ergänzt. Vorher gelten sie als **NOT RUN**.

## Übernommene Basis und Prüfvertrag

Basis ist P169 `99fb90fc855c4c7643e24816fa644fdc738c290f`, einschließlich
P166 `6395d4cf1d027ae2f01b73ed2a6e658121a469c9`, P168
`8ad695055cdaa0dafc99e3b1d1d61b83d9f30f14` und P165-Original-Faceplate.
P169 [Windows 42438260642](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42438260642)
meldet SUCCESS. Die vorherige P169-Ausführung auf `e1bbd5a` war fehlgeschlagen;
deren Ergebnis wurde ausdrücklich nicht als bestanden übernommen. P167s zwei
unveränderte PCM-Reproduktionen wurden als Tests übernommen, nicht dessen
Erwartung eines absichtlich fehlschlagenden Produkts in die Produktions-CI.
`main`, der bisherige Entwicklungsbranch und das Test-Lab-Repository bleiben unverändert.

Verbindliche Engineering-Quelle: `125A-Engineering`
`bc26392ec7ea9f20f074bff84bbc47ab439d5fe0`. START-HERE, README,
die vollständigen Engineering-Guardrails, Audit-Completeness-Contract und die
einschlägigen DSP-/GUI-/Repository-/Realtime-/Fixture-/Release-Standards wurden
vor der Produktänderung gelesen. Produkt-AGENTS, START-HERE, P166-/P167-Bericht
und Issues #80–83 wurden ebenfalls geprüft. AWE hat keinen veröffentlichten
FULL-/Gumroad-Referenzbuild; dieses Projekt ist weiterhin Vorabentwicklung.

## Reproduzierte Fehler und minimale Korrekturen

### F01: Kanal 10, ausdrücklich CC0=0, falscher tatsächlich vorhandener Klang

`Synth::BankNumberFor` benutzte `bankMsb==0` als Ersatz für „kein Bank-CC
empfangen“. Dadurch wurde eine ausdrückliche Null zu Bank 128. Die originalen
P167-Synth- und Processor-Tests reproduzierten vor der Änderung jeweils genau
den falschen Bankklang bei bestandener Gegenkontrolle zweier verschiedener Sounds.

`ChannelState::bankMsbTouched` trennt Empfangshistorie und Wert. CC0 setzt das Bit
auch bei wiederholter Null. Ohne Browser-/CC0-Auswahl bleibt Kanal 10 bei Bank
128. Browserwahl, bestehende gestempelte MIDI-Replay-Reihenfolge und neuere
Projekt-Recalls behalten ihren Vorrang. CC32 bleibt entsprechend dem bisherigen
Creative-Vertrag gespeichert, ist aber **kein zusätzlicher 14-Bit-SF2-Bankfaktor**.
Diese bestehende Einschränkung wird nicht als neue Hardwareerkenntnis ausgegeben.

### F02: Pad lässt sich trotz gehaltenem MIDI nicht zum Klick verkürzen

Die bisherige absolute Kennlinie ersetzte schon bei 1% die SF2-Zeit durch eine
fremde sehr schnelle Rate und wurde danach bis 100% wieder langsamer. SF2-Delay
und Hold blieben unangetastet. Der absichtlich lange synthetische Pad klang beim
Klickversuch länger als die drei Sekunden Aufnahme.

Die zwölf IDs bleiben bestehen. Attack-/Decay-/Release-Overlays interpolieren
jetzt von der tatsächlichen Patchrate zur schnellsten zulässigen Hardware-Rate
127. Attack verkürzt auch Delay und Hold proportional bis auf null. Sustain
reduziert den tatsächlichen Patch-Sustain relativ bis auf null. Keine Änderung
der Hardware-Hüllkurvenberechnung, keine nachgeschaltete Software-Hüllkurve.

Bedienung für kurze neue Noten: AMP A/D/S/R auf 100%. Im geprüften Pad endet
das Signal nach rund **45,1 ms einschließlich ca. 22,2 ms FIFO-Latenz**, während
die MIDI-Note 2,5 Sekunden gehalten wird. 0% bleibt Original, höhere Werte
bedeuten stärkeres Verkürzen bzw. Sustain-Absenken. Die Regler gelten weiterhin
bei **neuem NoteOn**, nicht rückwirkend für laufende Stimmen. Tooltips und
Host-Titel erläutern dies bei unveränderter Faceplate/Reglergeometrie.

Zusätzliche Selbstgegenprobe: Ein SF2-Release von 8000 Timecents wird als
Rate 0 kodiert; `StartVoice` spielt dafür außerhalb DOS bereits historisch Rate
0x40. Die neue Kennlinie muss von diesem tatsächlich gespielten Ersatzwert
ausgehen. Sonst stieg die späte RMS bei 0→1% von 0,00482 auf 0,04185.
Nach Korrektur: 0,00482 → 0,00444 → 0,00379 → 0 für 0/1/5/100%.
Auch diese Regression wurde vor der Korrektur durch PCM nachgewiesen.

**Kompatibilitätsgrenze:** V11-Bytes und ParamIDs bleiben lesbar/unverändert;
früher mit **nichtnull** gespeicherten fehlerhaften Overlays wird bewusst eine
korrigierte Klangbedeutung gegeben. Es wird keine PCM-Gleichheit für diese alten
fehlerhaften Kennlinien behauptet. Neutralzustände werden separat bitgenau geprüft.

### F03: FILTER ADSR ohne SF2-Filterroute akustisch wirkungslos

Die bisherige Zeitregisteränderung konnte einen nicht vorhandenen PEFE-Weg nicht
aktivieren. Eine SF2 ohne Generator 11 reproduziert konstantes statt abklingendes
Hochtonverhältnis. Bei Filter-Overlay und fehlender Route wird jetzt progressiv
ein **echter PEFE-Filterweg** eingeblendet, bis 96 von 127 Tiefenschritten. Der
Basis-Cutoff sinkt passend, der Peak liegt beim ursprünglichen Patch-Cutoff.
Vorhandene positive und negative Filterrouten und die PEFE-Pitch-Bits bleiben
erhalten. Keine Änderung am 86Box-Filter, kein zweiter Softwarefilter.

Hardwaregrenze: EMU8000 besitzt eine gemeinsame Modulationshüllkurve. Bereits im
Patch vorhandene Pitch-Modulation benutzt weiterhin dieselbe Hüllkurve. Dies
ist kein Versprechen zweier physisch unabhängiger Modulationsgeneratoren.

### F04: SF2 Loop-Until-Release mit kurzem Nachlauf wird nicht geöffnet

Die alte mindestens-20-Worte-Regel aus dem historischen SBK-Treiber wurde auch
auf SF2-Modus 3 angewendet. Ein korrektes SF2-Sample mit 16 Worten Nachlauf blieb
nach NoteOff im Loop. Für SF2-Modus 3 wird die Schleife jetzt unabhängig von
diesem SBK-Abstand geöffnet. Der restliche Sample-Nachlauf darf ausspielen;
Stille wird erst nach Sample-Dauer plus FIFO gefordert. Modus 1 bleibt im Loop
während Release; SF1/SBK-Referenzverhalten bleibt unverändert.

### F05: EndAddrsOffset / EndAddrsCoarseOffset werden ignoriert

Start- und Loop-Offsets wurden verarbeitet, das Sample-Ende dagegen immer aus
dem Header übernommen. Der neue Endwert berücksichtigt beide SF2-Generatoren
mit vorzeichenbehafteter 64-Bit-Arithmetik und Speichergrenze. One-Shot und
Release verwenden denselben Endwert. Die Gegenprobe enthält die erforderlichen
Null-Guardworte am effektiven Ende und wieder hörbare Samples dahinter; damit
unterscheidet sie ein wirklich falsches Ende von einer ohnehin stillen Datei.

## Keine unbelegten Produktänderungen

- Cutoff bleibt **Cutoff Reduction**: 0% Original, 100% tiefster Hardware-Cutoff.
  Eine Umkehr würde den geforderten neutralen Nullpunkt verletzen. Spektralmessung
  bestätigt die Absenkung; Resonanz erhöht das Verhältnis nahe Cutoff deutlich.
- Reverb und Chorus bleiben hardwaretypische **Sends**, kein Dry/Wet. Reverb-
  Nachklang steigt mit dem Send; bei Maximum bleibt das trockene Signal vorhanden.
  Chorus-Berechnung und originale Effektkoeffizienten wurden nicht geändert.
- Kein willkürlicher ROM-Boost. Die vorhandene 16-IFATN-Schritt-Kompensation bleibt.
  Der kontrollierte synthetische ROM-/DRAM-Vergleich richtet Root-Key, Loop,
  Velocity, CC7/11, Sustain und Send gleich aus und berücksichtigt die analytisch
  verschiedenen Quellamplituden. Das ist **kein Pegelnachweis der Original-GM-ROM**.
- Der gemeldete erste SF2-Ton konnte mit den verfügbaren synthetischen Dateien
  bislang nicht reproduziert werden. Erstes NoteOn nach akzeptiertem Laden wird
  bei drei Raten, vorhandenen Programmnummern und Engine-Tausch geprüft. Kein
  erfundener Lade-Race-Fix. Reale private SF2-/DAW-Reproduktion bleibt offen.

## Audioorakel, Negativkontrollen und Rohdaten

`tests/p170_audio_oracles.py` erzeugt eigene gültige SF2 mit drei analytischen
Harmonischen, langen Delay-/Hold-Zeiten und expliziten Loopfällen. Der separate
Transport `p170_audio_render.cpp` schreibt tatsächlich vom 86Box-Chip gerenderte
int16-Stereo-PCM. Entscheidungen benutzen RMS-Zeitfenster, harmonische Projektion,
absolute Dauer und erste/letzte Signalausgabe. Kein Vergleich nur auf „Parameter
hat sich verändert“. Sweeps: 0/1/5/20/50/75/100% für AMP-/Filter-ADSR und Cutoff;
zusätzlicher Q-/Send-Sweep. 44,1/48/96 kHz und 128/256/511-Frame-Blöcke.

Sechs separat kompilierte Testmutanten: (1) alte CC0-Null-Verwechslung,
(2) AMP-Attack/Delay/Hold nicht verbunden, (3) neue Filterroute getrennt,
(4) alte 20-Worte-Loopbeschränkung, (5) Endoffset ignoriert, (6) ROM-Kompensation
entfernt. Testcode verlangt gezielte **akustische FAILs mit Exitcode 1**;
Crash/Setupfehler/Timeout gelten nicht als erkannte Mutation. Der positive
Produktlauf wird vorher ausgeführt. Mutantdateien entstehen ausschließlich im
Buildverzeichnis; keine davon wird in die VST3 eingebunden.

`p170_compare_baseline.py` kompiliert die **gepinnte P169-Quelle** neben dem
Kandidaten und führt identische Stimuli aus. Alte Fehler müssen reproduziert
werden; unbetroffene Neutralfälle müssen bytegleich bleiben. In der ersten
lokalen Gegenprobe: **14 Neutralfälle / 8.078.400 PCM-Bytes bitgleich**.
Modus-3-Release und Endoffset sind bewusst korrigierte Ausnahmen.

`p171_processor_contract.cpp` benutzt den unverändert extrahierten tatsächlichen
Processor, echte Steinberg-Queues und EventLists. 16 Kanäle × Bank0/5,
wiederholtes CC0/CC32, Programmwahl, Engine-Tausch und neuere Recalls werden
gegen vorhandene unterschiedliche PCM-Sounds verglichen. Der zusätzliche native
Windows-Host lädt die **exportierte Produkt-DLL** samt echtem Controller und
prüft erste Noten nach SF2-Load-Nachricht bei 44,1/48/96 kHz und Programm0/7/9.
Er ersetzt keinen interaktiven SF2-Dateidialog im Nutzerhost.

Der neue Stress schreibt jeden gemessenen Callback nach `p171-rt.csv`:
44,1 kHz, 128/256/512/1024 Frames, 1/16/30 NoteOn-Identitäten, sechs Lastarten
(Render, Save, Save+Recall, MIDI-/Pitchautomation mit Recall, bewegte neue
Filterroute bei exakt gehaltener Last, Filterroute mit Retrigger/FX/Recall),
je 200 Blöcke: **14.400 process()-Messungen je Lauf**. Die zusätzliche
synthetische Filter-Stressbank hält ihren Modulations-Attack über den gesamten
Messabschnitt in Bewegung. Die ursprüngliche neutrale Fixture bleibt bytegleich. Host-Pufferbau/PCM-Kopie liegt außerhalb
der Zeitmessung. Windows zusätzlich rohe Threadzyklen, Kernnummern, QPC-Beginn/
-Ende/Frequenz und PID/TID. Zyklen werden nicht in angebliche CPU-ms umgerechnet.
Median/p99/Maximum/Misses und Held-Min/Max werden pro Zelle ausgewiesen.

**Recall und dichtes Retriggern können die gehaltene Last reduzieren**:
Auch Creative Voice-Stealing bei noch lauten freigegebenen Stimmen wird im
Held-Min/Max sichtbar. Die separate bewegte Filter-Haltelast verlangt ausdrücklich
unverändert 1/16/30 zugeordnete Identitäten; sie benutzt keine Retrigger, die
andere gehaltene Stimmen stehlen könnten. Für die Recall-/Retrigger-Zellen gilt: diese Fälle dürfen nicht als
Beschleunigung gegenüber voll klingenden 30-Stimmen-Zellen interpretiert werden.
Dies sind Offline-Laborzeiten ohne ASIO/MMCSS. Optional aufgezeichnetes WPR-
GeneralProfile wird archiviert, ohne unanalysierte Schedulerursachen zu behaupten.
C++-`new`-Audit P130 bleibt aktiv; er deckt **nicht** malloc/realloc/HeapAlloc ab.

## Abnahme- und Vollständigkeitsmatrix

| Bereich | Nachweis | Grenze |
|---|---|---|
| F01 Bankklang | P167 Originalproben + 16-Kanal-Processor-PCM + Bank-Mutant | Originaldateien/DAW separat |
| AMP ADSR | gehaltenes Pad→Klick, Zeit-/RMS-Sweeps + AMP-Mutant | laufende Stimmen behalten NoteOn-Parameter |
| Filter ADSR | fehlende/positive/negative Route, spektrale ADSR-Sweeps + Filter-Mutant | gemeinsame Hardware-Modulationshüllkurve |
| Cutoff / Q / Sends | Frequenzkomponenten und zeitlicher Effekt-Nachklang | kein neues Hardware-Rundungsorakel |
| erste Note | synthetische tatsächliche Processor-/exportierte DLL-Ausgabe | Original-Nutzerproblem nicht reproduziert |
| Loops/Endoffset | Modi0/1/3, kurze Tail, PCM + Loop-/End-Mutant | keine vollständige Original-SF2-Presetabnahme |
| ROM-Pegel | analytischer synthetischer Vergleich + Kompensations-Mutant | Original-ROM/SYNTHGM/private SF2 NOT RUN |
| State/Automation | bestehende P122/P128/P133 + P171-Konkurrenzstress | keine kommerzielle DAW-Projektsitzung |
| RT / Speicher | Callback-Rohdaten, bestehender C++-Heaptest, ASan/UBSan/LSan | kein Zielrechner-/vollständiger Windows-Heapnachweis |
| GUI | P165/P168/P169 übernommen, voller Win32-EditorHost-/Pixel-Retest | persönliche Nutzer-DAW-Abnahme NOT RUN |
| Test Lab | unabhängig gepinnte unveränderte Hosts, Produkt-DLL-Hash | generisches `preset_semantics=NOT COVERED` bleibt ehrlich |
| Quellreview | Synth, SoundFont, Factory und geänderte Einheiten nachvollzogen | große unveränderte DSP-/Legacy-/Testbereiche nur teilweise gelesen |
| adversarialer Review | explizite Signalorakel, Vorher/Nachher und Mutanten | **SELF-CHALLENGE**, kein zweiter unabhängiger Auditor |

Das ergänzende Dateiinventar enthält SHA-256 und Reviewstatus. Ein vorhandener
Pfad ist kein semantisch abgeschlossener Review. Insbesondere vollständige
86Box-/Upstream-Durchsicht, alle historischen Testassertionen, alle GUI-Host-
Randfälle und Hardwarehörvergleich sind nicht lückenlos belegt. Der
Audit-Completeness-Contract ist deshalb **NICHT vollständig erfüllt**.

## Verbleibende Grenzen und Entscheidungen

Keine Original-Wave-ROM, SYNTHGM.SBK oder private Nutzer-SF2 in dieser Umgebung
gefunden; nur synthetische Fixtures. Ihre tatsächliche EMU8000-Wiedergabe,
Lautheits-/Loop-/First-Note-Vergleiche sowie Ziel-DAW und physisches ASIO bleiben
**NOT RUN**. Kein Ausweichen auf einen anderen SF2-Player als angeblichen
Hardwarebeweis und keine Veröffentlichung privater Samples.

Lokaler vollständiger Release-CTest-Lauf: **51/51 PASS**, einschließlich sechs
akustisch erkannten Mutanten und gepinnter Vorher-/Nachher-Gegenprobe. Dies ist
kein Windows-Modulvalidator-Ergebnis.

Die zusätzliche vollständige Debug-Sanitizerprobe fand außerdem in der
unveränderten, im EMU-VST3 nicht aufgerufenen historischen CQM-Testkomponente
`third_party/Nuked-CQM/cqm.c:277` einen negativen Links-Shift (`wave_prev << 2`).
Der betreffende Legacy-C-Test bekommt **FAIL**, kein pauschaler Sanitizer-PASS.
Die vendorte Referenz wurde nicht nebenbei verändert. Der SDK-Validator-
Selbsttest des instrumentierten Linux-SDK meldete zusätzlich 6.124 Leak-Bytes
in 95 Registrierungs-/Testobjekten; auch dieser externe Tool-Lauf ist kein
Sanitizer-PASS. Die 37 tatsächlichen AWE-Projektziele wurden separat erfolgreich
instrumentiert gebaut. AWE-spezifische
ASan/UBSan/Leakprüfungen werden getrennt ausgewiesen.

**Kommerzielle Freigabe: NO-GO. FULL AUDIT: NOT COMPLETE.
Echtzeit-Zielrechnerabnahme: NOT RUN.** Ein grüner Windows-Lauf ändert diese
Beweisgrenzen nicht. Keine eigenmächtige Promotion nach main oder Releasepaket.

## Exakte neue Ausführungsnachweise

Wird nach Abschluss der Windows-Matrix mit Quell-SHA, beiden Run-/Jobnachweisen,
VST3-PE-Hashes, CTest-/Validator-/GUI-/Test-Lab-Zahlen und Callbackstatistik ergänzt.
