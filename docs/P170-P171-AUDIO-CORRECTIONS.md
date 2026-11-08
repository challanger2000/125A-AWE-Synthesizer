# P170/P171 — Funktionskorrekturen und falsifizierbare Audioprüfung

Stand 2026-11-08. Branch `fix/p170-p171-audio-corrections`.
**Entwicklungsprüfung; kein FULL AUDIT, kein Release, kein Merge.**
Endgültiger Produkt-/Teststand `b02e02d472544eb2122533f9b8d7dc9d0b97f68a`:
Windows A/B funktional bestanden. **RT-Matrix: FAIL (1/28.800 Deadlines)**;
der einzelne Ausreißer ist per verlustfreiem ETW durch Ready-Preemption
hinreichend erklärt. Physische Echtzeit-Zielrechnerabnahme: **NOT RUN**.

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

### F06: obere Reglerbereiche bei nichtneutralen Patches wirkungslos

Der alte volle additive Offset erreichte die Registergrenze vorzeitig: Cutoff
bei 75%, Q und beide Sends bei 50% erzeugten bei geeigneten nichtneutralen
Patches dasselbe tatsächliche PCM wie 100%. Der neue relative Eingriff benutzt
nur den verbleibenden Weg zum jeweiligen Hardware-Endpunkt. 0% bleibt das
Original; 100% erreicht weiterhin denselben Endpunkt. Damit funktionieren auch
die oberen Reglerbereiche, vorbehaltlich der endlichen Hardware-Quantisierung.
Die neue Gegenprobe verwendet SF2-Cutoff9000, Q100 und Sends500 und wird gegen
P169 sowie durch eine gezielte Reverb-Kennlinien-Reversion falsifiziert.
Bei den Sends wird auch der bereits vorhandene Kanalanteil aus CC91/93 vom
verbleibenden Bereich abgezogen. Ohne diesen Schritt sättigte selbst die erste
relative Korrektur mit CC127 wieder vorzeitig. Zwei weitere PCM-Gegenproben
reproduzierten dies; sie bestätigen vor dem Audiovergleich ausdrücklich die
tatsächlich geschriebenen kombinierten Original-Sendwerte 242/241.
Keine Änderung der Filter-/Reverb-/Chorus-DSP-Rechenregeln.

Beispielwerte der endgültigen nativen PCM-Probe: Die neue Filterroute senkt
das obere/untere Harmonischenverhältnis von 0,201681 auf 0,00408943; P169
blieb bei 0,405943 → 0,411266. Der Resonanz-Sweep erhöht das Verhältnis
der fünften Harmonischen zur Grundschwingung von 0,429766 auf 4,92162.
Die Reverb-Tail-RMS bei 0/20/50/100% beträgt 0 / 0,001123 / 0,002832 /
0,005650; der vom trockenen Signal abgezogene Chorus-Rest 0 / 0,018098 /
0,045421 / 0,090488. Das sind synthetische spektrale Stichproben und
Zeitfenster, kein lückenloser Hardware-Frequenzgangvergleich.

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
zusätzlicher Q-/Send-Sweep, nichtneutrale Patch-Ausgangswerte, CC64-Pedal und
feiner/grober Sample-Endoffset. 44,1/48/96 kHz und 128/256/511-Frame-Blöcke.

Acht separat kompilierte Testmutanten: (1) alte CC0-Null-Verwechslung,
(2) AMP-Attack/Delay/Hold nicht verbunden, (3) neue Filterroute getrennt,
(4) alte 20-Worte-Loopbeschränkung, (5) Endoffset ignoriert, (6) ROM-Kompensation
entfernt, (7) Sustainpedal ignoriert, (8) früh sättigende Reverb-Kennlinie
wiederhergestellt. Testcode verlangt gezielte **akustische FAILs mit Exitcode 1**;
Crash/Setupfehler/Timeout gelten nicht als erkannte Mutation. Der positive
Produktlauf wird vorher ausgeführt. Mutantdateien entstehen ausschließlich im
Buildverzeichnis; keine davon wird in die VST3 eingebunden.

`p170_compare_baseline.py` kompiliert die **gepinnte P169-Quelle** neben dem
Kandidaten und führt identische Stimuli aus. Alte Fehler müssen reproduziert
werden; unbetroffene Neutralfälle müssen bytegleich bleiben. In der abschließenden
lokalen Gegenprobe: **21 Neutralfälle / 11.782.800 PCM-Bytes bitgleich**.
Modus-3-Release einschließlich Pedal und die Endoffset-Fälle sind bewusst
korrigierte Ausnahmen.

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
Das verwendete obere p99 ist der sortierte Wert am nullbasierten Index
`floor(0,99 * N)` (bei N=200: Index198); alle 200 Werte bleiben erhalten.
Solche kurzen Zellen begründen keine statistische Langzeit-Tailgarantie.
Diese Zeitmessung verwendet den quellidentisch extrahierten Processor mit
leeren Test-Hooks im Testprogramm, **nicht die exportierte Shipping-DLL**.
Die zusätzliche DLL-Probe prüft deren Funktion, nicht deren Callbackzeiten.
Damit wird die neue Matrix nicht als unmittelbarer DLL-/ASIO-Zeitnachweis
ausgegeben; ältere P139/P140-DLL-Messungen ersetzen diesen Nachweis ebenfalls
nicht für den geänderten P170/P171-Stand.

**Recall und dichtes Retriggern können die gehaltene Last reduzieren**:
Auch Creative Voice-Stealing bei noch lauten freigegebenen Stimmen wird im
Held-Min/Max sichtbar. Die separate bewegte Filter-Haltelast verlangt ausdrücklich
unverändert 1/16/30 zugeordnete Identitäten; sie benutzt keine Retrigger, die
andere gehaltene Stimmen stehlen könnten. Für die Recall-/Retrigger-Zellen gilt: diese Fälle dürfen nicht als
Beschleunigung gegenüber voll klingenden 30-Stimmen-Zellen interpretiert werden.
Dies sind Offline-Laborzeiten ohne ASIO/MMCSS. Optional aufgezeichnetes WPR-
GeneralProfile wurde anschließend im separaten Auditbranch kausal ausgewertet;
Einzelheiten und vollständige Grenzen stehen im Nachweis unten.
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
| State/Automation | bestehende P122/P128/P133 + P171-Konkurrenzstress, gehaltene Note bei Overlay-Automation | keine kommerzielle DAW-Projektsitzung |
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

Lokaler vollständiger Release-CTest-Lauf: **53/53 PASS**, einschließlich acht
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
ASan/UBSan/Leakprüfungen am endgültigen Quellstand
`b02e02d472544eb2122533f9b8d7dc9d0b97f68a`: **39/39 PASS**, 644,61 s,
Leak-Erkennung aktiv, UBSan/ASan jeweils mit sofortigem Fehlerabbruch.
Keine ThreadSanitizer-Abnahme. Der uninstrumentierte vollständige lokale Lauf
bestand **53/53 in 257,21 s**. Ausgaben, 116 synthetische PCM-Messfälle mit
40 Signalentscheidungen, acht Negativkontrollen und Vorherdaten liegen dauerhaft
unter [docs/evidence/P170-P171](evidence/P170-P171/README.md).

**Kommerzielle Freigabe: NO-GO. FULL AUDIT: NOT COMPLETE.
Echtzeit-Callbackmatrix: FAIL (1/28.800); Zielrechnerabnahme: NOT RUN.** Ein grüner Windows-Lauf ändert diese
Beweisgrenzen nicht. Keine eigenmächtige Promotion nach main oder Releasepaket.

## Exakte neue Ausführungsnachweise

Die Korrekturen sind ausschließlich auf `fix/p170-p171-audio-corrections`:

- `6eeee366dd23f82106a29772e4297395997be8b3`: F01–F05, echte PCM-Orakel,
  Testmutanten und eigene Windows-Matrix.
- `568da06bd47838740818c2ab9f2dfaa11f599426`: tatsächliche Release-Rate0-
  Ersatzrate als Ausgangspunkt, mit reproduzierter Vorherregression.
- `330eaa28c9bc29d93ebe34e76c2521905a0f7038`: bewegte Filter-Haltelast
  bei allen drei Stimmenzahlen, zusätzliche Retrigger-/Recall-Last.
- **Endgültiger geprüfter Produkt-/Teststand
  `b02e02d472544eb2122533f9b8d7dc9d0b97f68a`**: F06 einschließlich
  MIDI-Send-Anteil, Pedal-/Coarse-End-/Held-Automation-Gegenproben,
  acht Mutanten, dauerhafte öffentliche Roh-CSV-Zusammenfassung.

Die früheren Windows-Matrizen
[42440416814](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42440416814),
[42440868070](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42440868070)
und [42441854447](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42441854447)
waren erfolgreich, sind aber **kein Endnachweis des danach geänderten Stands**.
Die endgültige Windows-Matrix
[42479356487 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42479356487)
prüfte genau diesen Stand. Alle unten ausgewiesenen Produktprüfungen sind in
beiden Jobs erfolgreich; Deadline-Misses sind eine separate Messentscheidung
und werden nicht durch den grünen Workflow überschrieben.

| Nachweis | Windows A | Windows B |
|---|---:|---:|
| Job | [128727698242](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42479356487/job/128727698242) | [128727698005](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42479356487/job/128727698005) |
| vollständige CTests | 62/62 | 62/62 |
| tatsächlicher VST3-Modulvalidator | 537/537 | 537/537 |
| EditorHost-Smokes | 3/3 | 3/3 |
| reale Win32-GUI-/Pixelentscheidungen | 99/99 | 99/99 |
| unverändertes Test Lab | TECHNICAL_PASS | TECHNICAL_PASS |
| Callback-Messwerte | 14.400 | 14.400 |
| Deadlineüberschreitungen | 0 | **1** |

Beide Läufe: acht erkannte Negativmutanten, 40 positive Audioentscheidungen,
21 bitgleiche Neutralfälle/11.782.800 Bytes gegenüber P169, echte exportierte
VST3-DLL mit Controller für neun First-Note-Fälle. Test Lab exakt
`4267c86065bc8665b7af056f08af0a08760256d4`, ohne Repositoryänderung;
sechs generische Host-/State-/GUI-/Instanzbereiche PASS, `preset_semantics`
bleibt dort ausdrücklich NOT COVERED. Produktspezifische Klangentscheidungen
liegen in den gesonderten P170/P171-Orakeln.

Tatsächlich vom Test Lab geladene VST3-PE-SHA-256:

- A: `eaef9ce93d40708b05836dcc2b879242ed698089452f37afcb80847c99bf8eeb`
- B: `49039da8c39da09b92fd909a258711817477facd7be61ff87500699f16a29f40`

Testpakete, **keine Releases**:
[P170-P171-Windows-x64-VST3-TEST-A](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42479356487/artifacts/13617630557) und
[P170-P171-Windows-x64-VST3-TEST-B](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42479356487/artifacts/13616744624).
Vollständige synthetische PCM-/GUI-/ETL-/Test-Lab-Rohbeweise:
[Full-Regression-A](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42479356487/artifacts/13617056974) und
[Full-Regression-B](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42479356487/artifacts/13616968364).
Actions-Aufbewahrung: Testpaket sieben Tage, QA 14 Tage. Dauerhafte numerische
Beweise und Artefaktdigests stehen unter `docs/evidence/P170-P171`.

### 128 Frames / 30 gestartete Identitäten: alle sechs Lastarten

Alle Zeiten in µs, jeweils 200 Callbacks. Das Budget beträgt 2.902,49 µs.
Eine Reduktion der gehaltenen Last bei Recall/Retrigger ist kein Performancegewinn.

| Lauf | Last | Median | oberes p99 | Maximum | Misses | Held min–max |
|---|---|---:|---:|---:|---:|---:|
| A | Render | 805.90 | 1138.80 | 1188.10 | 0 | 30–30 |
| A | Save | 807.10 | 1306.80 | 1310.30 | 0 | 30–30 |
| A | Save+Recall | 185.50 | 1146.90 | 1212.70 | 0 | 0–30 |
| A | MIDI/Pitch+Recall | 191.95 | 1201.00 | 1239.40 | 0 | 0–30 |
| A | bewegter Filter, gehalten | 1536.30 | 2004.30 | 2065.20 | 0 | 30–30 |
| A | Filter/FX/Retrigger+Recall | 833.10 | 1577.90 | 1658.70 | 0 | 0–12 |
| B | Render | 657.20 | 945.80 | 970.00 | 0 | 30–30 |
| B | Save | 950.65 | 1901.30 | 3959.00 | 1 | 30–30 |
| B | Save+Recall | 157.10 | 931.90 | 1241.20 | 0 | 0–30 |
| B | MIDI/Pitch+Recall | 161.40 | 927.30 | 965.70 | 0 | 0–30 |
| B | bewegter Filter, gehalten | 1275.95 | 1751.30 | 1924.10 | 0 | 30–30 |
| B | Filter/FX/Retrigger+Recall | 906.20 | 1326.30 | 1878.90 | 0 | 0–12 |

Alle 72 Zellen pro Lauf einschließlich 256/512/1024 Frames und 1/16 Stimmen
stehen mit Median/p99/Max/Misses/Held-Min/Max in `windows-*-summary.json`.
Die bewegte Filter-Haltelast behielt in beiden Läufen in **allen zwölf Zellen**
exakt die geforderten 1/16/30 Identitäten. Recall-Zellen fielen bis auf null,
128/30 mit dichtem Retrigger sogar auf 0–12: diese Zeilen sind kein fairer
CPU-Vergleich mit durchgehend klingenden 30 Stimmen.

### Kausaler ETW-Nachaudit des einzelnen Deadline-Ausreißers

Audit-only Branch `audit/p171-etw-b02e02d`, Decoder-/Analysestand
`dce06d3d3de3517082588800f4706e96cd619a5d`;
[Windows-Audit 42480859178 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42480859178).
Er lädt exakt die ursprünglichen A/B-QA-Artefakte und verifiziert deren zuvor
veröffentlichte Summary- und Roh-CSV-Hashes. Keine ersetzte Stressmessung.
TDH decodiert rohe QPC-CSwitch-Ereignisse. Zwei Schlaf- und zwei Busy-Kontrollen
je Decoderlauf bestanden, ebenso analytische Gegenproben für falsche Uhr,
Eventverlust, fehlende Intervallgrenzen, Waiting und Ready-Preemption.
Die Kalibrierung liegt auf dem Auswertungsrunner, nicht rückwirkend im Originaltrace.

Originaltrace A: 2.383.622 Ereignisse, 2.124 relevante CSwitch;
B: 3.386.847 Ereignisse, 8.130 relevante CSwitch.
Beide: **0 verlorene Events/Buffers**, QPC 10 MHz und lückenlose
On-/Off-Intervallabdeckung für sämtliche **14.400/14.400** Callbackfenster.

Der einzige Miss ist in B, 128/30/Save, Block173, PID724/TID1088:

| Messgröße | µs |
|---|---:|
| ursprüngliche Callback-Wandzeit | 3.959,0 |
| äußeres QPC-Fenster | 3.959,1 |
| Audiobudget | 2.902,49 |
| eingeplante Threadlaufzeit | 1.494,2 |
| Off-CPU, Zustand Ready | **2.464,9** |
| Waiting | 0,0 |

Der Thread wechselt von Kern3 auf Kern0. Ready-Off-CPU ist größer als der
Budgetüberschuss; die eingeplante Laufzeit bleibt unter Budget. Damit ist
**READY_PREEMPTION_SUFFICIENT** für diesen konkreten Ausreißer nachgewiesen.
Es ist kein Beleg eines Plugin-Lock-Wartens; die eingeplante Zeit enthält
Interrupts und sonstige Ausführung und ist **keine reine DSP-Zeit**.
Kein spekulativer DSP-Eingriff und keine veränderte Messpriorität zur kosmetischen
Entfernung des Ausreißers. Unbeobachtete Zielrechner-/ASIO-/Langzeitbedingungen
bleiben offen. GeneralProfile begründet weiterhin **keinen vollständigen
malloc/realloc/HeapAlloc-Nachweis**.

**Entscheidung:** Funktionale Windows-Abnahme PASS im beschriebenen Umfang.
Deadlinefreie Callbackmatrix **FAIL (1/28.800)** trotz erklärtem Scheduleranteil.
Echte Zielrechner-Echtzeitabnahme **NOT RUN**, FULL AUDIT NOT COMPLETE,
RELEASE NO-GO. Die separate Auditdiagnostik wird nicht in den Produktbranch gemergt.

Die vollständigen ursprünglichen Callback-CSVs sind dauerhaft als
`docs/evidence/P170-P171/windows-A-callbacks.csv.gz` und `windows-B-callbacks.csv.gz`
abgelegt: je 14.400 ungefilterte Zeilen, Original-QPC/PID/TID/Kerne/Zyklen/Last und
Wandzeit. Ihre bereits im ursprünglichen Lauf veröffentlichten SHA-256 wurden
nach Rekonstruktion geprüft und **sämtliche 72 Zellstatistiken je Lauf** lokal
aus diesen Rohzeilen exakt nachgerechnet. Publikationsstand des separaten Audits:
`93441628edc0c5d9bb341c9f5f423dab2914ea8c`,
[Sicherungslauf 42481489720](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42481489720).
Die ETL-/CSwitch-/Kontroll-Rohdateien liegen zusätzlich in den 30-Tage-Artefakten
`P171-ETW-Original-b02e02d-A/B` des kausalen Audits 42480859178.
