# Unabhängige SF2-Dämpfungs- und Clipping-Untersuchung, 11.11.2026

**Ergebnis: zwei Produktabweichungen beim SF2-Upload und bei der IFATN-Dämpfung sind nachgewiesen. Die 117 nativen Clipping-Fälle sind reproduziert. Keine produktive Klangkorrektur wurde übernommen. Klangabnahme BLOCKED; physische AWE-Hardware und echte Windows-VST3-Besitzerbank-Aufnahmen NOT RUN.**

Der korrigierte Auftrag betrifft ausschließlich SF2-Dämpfung, Layer und Clipping.
Die Cutoff-Untersuchung bleibt beim Entwicklerchat. Es wurden keine neuen Branches,
Merges, Klangpfad-, Filter-, Chorus- oder ASIO-Grenzwertänderungen vorgenommen.
Das Plugin Test Lab wurde nicht verändert. Wiederverwendet wurden P228/P229,
P48/P63/P64/P67/P83/P89 und die vorhandenen P233/P234-Beobachter.

## Identitäten und tatsächlich ausgeführte Läufe

- Gemessener Produktkern: `8d2f41dfefd84d98a903ee8c3bdfe0350ae9de95`, unveränderter Snapshot des Entwicklerbranches `qa/p230-original-rom-sbk-audio`. Dieser Branch war nach den Messungen bereits bei `3d2a1a3bdd7a1f49390f3b79305fbc9b174a3112`. **Keine Behauptung über dessen ungemessene spätere Änderungen.**
- Diagnose-/Teständerungen ausschließlich auf dem bereits bestehenden Branch `fix/creative-volume-sustain-layer-parity`, getesteter Commit `ca68572c4fee0693e6e21ab59d0417dc46196e34`. Dessen Produktbasis ist älter als der gemessene Entwicklerkern; es fand keine Produktintegration zwischen diesen Ständen statt.
- Originalreferenz: tatsächlich gebootetes Windows 95 OSR2, originale Creative-Dateien aus dem vorhandenen P38-Verfahren, originaler AWE-Control-Panel-SF2-Ladevorgang, echter WinMM-/COM1-Pfad, 86Box AWE64 Gold mit **28 MiB** Sample-RAM. Keine Ersatzregister als Originalreferenz eingespeist.
- 86Box-Quellcommit `d1d59ca9f57ed1df0c9e83243d258c19dcbe5da4`, Binär-SHA-256 `8d9dcbd655206c061f3b8a06dc7c2779d15cf5668ef50f977cef903671c83154`. Änderungen nur als vorhandene opt-in P45/P65/P233/P234-Lesebeobachter in einer verworfenen lokalen Emulator-Kopie; kein DSP-Rechenausdruck geändert.
- Wiederhergestelltes vorhandenes Win95-Ausgangsimage: 536.870.912 Bytes, SHA-256 `fb685b36b15123af51bad9b68b3402671837065f330b33778bfc771ccfd33c26`.
- Alle vier neu beigefügten SF2-Dateien stimmen in Größe und SHA-256 mit dem ursprünglichen P228-Inventar überein. [Quellmedien-Hashes](../qa/p229-independent-20261111/source-media-hashes.json). Gleiche Original-ROM auf beiden Seiten: SHA-256 `4e143b94f758734f594ded78f4e5115635975c16fa37fabeae0baa4938ca710e`.

Die beigefügte 3.082-Zeilen-CSV ist ein **Eingabeplan**, keine wiedergefundene 117er-Ergebnismatrix. Deshalb wurde die vollständige P228-Messung erneut ausgeführt und die 117er-Liste daraus neu abgeleitet.

| Originalbank | P228 echte Noten | Clipping-Fälle | Signed16-Rail-Werte | P229 V112 + V48 |
|---|---:|---:|---:|---:|
| Synth 512 Bank(3).sf2 | 688 | 28 | 2.169 | 56 |
| FM Dreams Sampler(1).sf2 | 210 | 5 | 92 | 10 |
| Vintage Dreams Bank.sf2 | 1.272 | 52 | 7.694 | 104 |
| Vintage Synth 2001.sf2 | 912 | 32 | 2.377 | 64 |
| Gesamt | **3.082** | **117** | **12.332** | **234** |

Alle 117 Fälle liegen auf Bank 0, Velocity 112; für jeden existiert die exakt gleiche Programm-/Noten-Kontrolle mit Velocity 48. P229 bestätigt **12.328 echte Signed32-Überbereichswerte**, davon 9.372 negativ und 2.956 positiv. Vier zusätzliche Rail-Werte liegen genau auf einer Rail. Das sind keine vier falsch klassifizierten Fälle. Alle 117 V48-Kontrollen bleiben unter der Übersteuerungsgrenze. Maximaler nativer Peak: **+5,822333 dBFS**. Kein fehlender aktiver Ton, keine stille Aufnahme, keine effektiven nativen FX-Sends bei GUI 0.

Jeder der **41.277.600** P229-Samplewerte wurde extern gegen `clip16(raw32)` geprüft: **0 Abweichungen**. Optionaler Register-/PCM-Mitschnitt und die vorhandenen P233/P234-Beobachter ändern **kein Byte** der 234 nativen PCM16- oder Raw32-Aufnahmen. [Bitgenauer Beleg](../qa/p229-independent-20261111/native-p234-observer-bitexact.json).

## Nachweis 1: falscher SF2-Sample-Upload

Aus den tatsächlichen Original-Creative-I/O-Schreibzugriffen wurden SMALW und SMLD dekodiert und die beschriebenen RAM-Adressen rekonstruiert. **Jedes einzelne smpl-Wort aller vier Banken wurde als Original-DMA-Schreibwert beobachtet**. Der Upload beginnt bei `0x200010`; die CCCA-Startadresse enthält dagegen den bekannten Startvorlauf. Diese Adressen dürfen nicht verwechselt werden.

| Bankindex | Beobachtete smpl-Wörter | Gegen unverändertes SF2-PCM verschiedene Wörter | Einfache Ganzsample-/8-Präemphase: verbleibende Unterschiede |
|---|---:|---:|---:|
| 0 | 260.921 | 257.552 | 102 |
| 1 | 693.475 | 692.253 | 32 |
| 2 | 125.160 | 121.585 | 62 |
| 3 | 2.234.719 | 2.220.521 | 260 |

`Synth::LoadBank()` des gemessenen Kerns kopiert SF2-PCM unverändert. Die vorhandene Creative-Upload-Präemphase wird ausschließlich für SF1 angewendet. **Die Original-Creative-Schreibwerte widerlegen unveränderten SF2-Upload unmittelbar**, unabhängig von Filter, DSP-Revision, Audio-Abgriff oder Hörurteil.

Das bekannte /8-Modell erklärt den überwiegenden Anteil, aber noch nicht alle SF2-Sonderfälle. Insbesondere unterscheiden sich Ganzsample-Ende, Nullbereiche und SF1s `end-3`-Regel. **Eine ungeprüfte Erweiterung der SF1-Bedingung auf SF2 ist keine freigegebene Korrektur.** Die exakten beobachteten DMA-Wörter bleiben privat verfügbar; es wird keine allgemeine bitgenaue SF2-Uploadformel behauptet.

Kausale Gegenprobe im **bestehenden P229-Diagnoseprogramm**, mit unveränderter statischer Produktbibliothek: Nach `LoadBank` ausschließlich die tatsächlich beobachteten Original-RAM-Werte einsetzen, alle übrigen MIDI-, GUI-, DSP- und Ausgabebedingungen gleich lassen. Ergebnis: **117 → 4** übersteuernde native Fälle; nur noch **24** Überbereichswerte. Dies ist eine diagnostische Einzelvariablen-Intervention, keine Produktkorrektur.

## Nachweis 2: doppelte Umrechnung der SF2-Dämpfung

Physische Stimmenummern und Layerreihenfolge unterscheiden sich beim Originaltreiber. Deshalb wurden Stimmen anhand tatsächlicher Sample-/Loop-Adressen und anschließend Pan/Pitch zugeordnet, nicht anhand ihrer Nummer. Für **790 vergleichbare Layer** stimmen die Sample-Adressen überein. Die zusätzlichen acht nativen Layer werden ausdrücklich separat ausgewiesen.

Der aktuelle Pfad skaliert `initialAttenuation` zunächst mit `0.4`, rundet in Registereinheiten und konvertiert diese in `ComputeAttenuationVxd()` erneut in dessen internes Zahlenformat. Das entspricht bei den vorliegenden SF2-Generatoren nicht dem originalen VXD-Eingabewert. Die Originalmessung wird dagegen erklärt durch:

```text
X = ursprünglicher SF2-initialAttenuation-Wert in Centibels
atten = ((volumeDb + velocityDb + (X + 12) / 24) * 8) / 3
```

Hier sind die Divisionen ganzzahlig. Bei den tatsächlich geprüften CC7=100/CC11=127 ist `volumeDb + velocityDb` gleich 6 für V112 bzw. 21 für V48. Die Aussage ist auf die gemessenen Werte **0, 80, 100, 150, 250** und diese Controllerbedingungen begrenzt; keine Behauptung über ungeprüfte Generatorgrenzen, Preset-/Instrument-Vorzeichenkombinationen oder sämtliche Controllerwerte.

| SF2-Centibels | V112 nativ → Creative | V48 nativ → Creative |
|---:|---:|---:|
| 0 | 16 → 16 | 56 → 56 |
| 80 | 24 → 24 | 64 → 64 |
| 100 | **24 → 26** | **64 → 66** |
| 150 | **29 → 32** | **69 → 72** |
| 250 | **37 → 42** | **77 → 82** |

**216/790 native IFATN-Lowbytes unterscheiden sich; 790/790 ursprüngliche Creative-Werte werden von der direkten Ganzzahlrechnung vorhergesagt.** Das ist ein belegter Kompatibilitätsfehler der Dämpfungsumrechnung, kein Anlass für eine pauschale Pegelnormalisierung oder einen modernen idealisierten SF2-Gain.

Zweite Gegenprobe: Im P229-Diagnoseprogramm zusätzlich ausschließlich die gemessenen IFATN-**Lowbytes** setzen. Alle IFATN-Filterbits bleiben unverändert; weder Filter- noch DSP-Dateien ändern sich. Zusammen mit Original-RAM: **117 → 2** Fälle, **13** Überbereichswerte. Die Registereingriffe ersetzen keine vollständige korrigierte Parametergenerierung und keine Produktregression. [Aggregat der Zuordnungen und Vorhersagen](../qa/p229-independent-20261111/attenuation-layer-register-analysis.json); vollständige private Einzelfalldaten werden über das [SHA-256-Manifest](../qa/p229-independent-20261111/PRIVATE-EVIDENCE-SHA256.json) authentifiziert und bleiben außerhalb von Git.

## Historisches Layerverhalten und weitere Abweichungen

Vintage Synth 2001, Programm 83/Note 60 und Programm 9/Note 84: Der originale Creative-Treiber aktiviert jeweils **6**, die native Engine **8** Layer, sowohl V112 als auch V48. Eine zusätzliche Wiederholung im frisch gebooteten Gast mit diesen Programmen bestätigt alle vier Fälle und exakt 60 zugestellte WinMM-Kommandos. [Frischgast-Gegenprobe](../qa/p229-independent-20261111/fresh-layer-count-witness.json).

Das ist eine reproduzierte Abweichung vom historischen **Creative-Treiberverhalten für diese Presets**, keine Behauptung, der EMU8000 könne allgemein höchstens sechs Layer. Die genaue Selektions-/Ladegrenze ist noch nicht allgemein bewiesen. Keine globale Layerbegrenzung implementiert. Außerdem bleiben 74/790 Pitch-Registerabweichungen und zwölf Pan-Abweichungen als getrennte Befunde dokumentiert; keine Filteränderung daraus abgeleitet.

## Messmethodik: gleicher Abgriff, echte Kanten, gleiche Fenster

234 tatsächliche Original-Creative-Noten wurden über den vorhandenen P64-Pfad gespielt. P67 bestätigt originalen Creative-WinMM-Endpunkt, laufenden Agenten, fehlerfreien Gast und genau **736/138/1.360/840** zugestellte Kommandos für die vier Banken. Das historische Agentenlog bestätigt die Gesamtzustellung, keinen individuellen Payload-Echo jedes Programmbefehls. Sample-Upload und tatsächliche nachfolgende Stimmenregister werden zusätzlich geprüft.

Die endgültige trockene Audiobewertung benutzt auf **beiden** Seiten den vorhandenen P234-Abgriff **vor Reverb, Chorus und Chip-EQ**, echte DCYSUSV-Schreibkanten und genau **88.200 Stereo-Frames bei 44.100 Hz**. Originale Haltedauer 44.084–44.099 Samples, nativ exakt 44.100; alle 234 Paare bestehen die vorhandenen drei ±44-Sample-Bedingungen. Keine Pegelnormalisierung, keine nachträglich angepasste Ausrichtung, keine unkontrollierte Übernahme kompletter DSP-Blöcke.

| Bankindex | Original: trockene Überbereichswerte | Nativ: trockene Überbereichswerte | Native trockene Clipping-Fälle |
|---|---:|---:|---:|
| 0 | 0 | 4 | 1 |
| 1 | 0 | 0 | 0 |
| 2 | 0 | 4 | 1 |
| 3 | 0 | 1.169 | 4 |
| Gesamt | **0** | **1.177** | **6** |

Die ursprünglichen **117** Fälle betreffen dagegen P229s tatsächliche native Ausgabe **nach** den weiteren Chip-Stufen und **vor** der Signed16-Sättigung. Diese Zahl darf nicht als 117 bereits vor dem EQ übersteuerte Stimmensummen umgedeutet werden. Zusätzliche Übersteuerung entsteht zwischen den beobachteten Stufen; damit ist noch kein Fehler einer konkreten DSP-Berechnung bewiesen.

Originales MIDI CC91/93=0 garantiert nicht, dass SF2-Preset-Sends und vorhandene Rückwege null sind: Die Originalbeobachtung zeigt in **184/234** Fällen tatsächlich Effektenergie, nativ mit GUI 0 dagegen **0/234**. Der Original-Post-FX/EQ-Tap enthält in einem Fall einen übersteuerten Frame (Bank 0, Programm 48/Note 99/V112). **Dieser Wet-Befund ist kein trockener Gegenbeweis und keine pauschale historische Rechtfertigung aller 117 nativen Fälle.** Der endgültige trockene Vergleich umgeht diese Verwechslung durch denselben Abgriff auf beiden Seiten.

Die frühen explorativen Vergleiche nativer Post-EQ-Ausgabe gegen Original-Pre-FX-PCM sind durch den hier dokumentierten gleichen Abgriff ersetzt und begründen keine Klangabnahme. [Aggregat und Methodik](../qa/p229-independent-20261111/sample-accurate-same-tap-comparison.json). Vollständige gleich lange Einzelfallmesswerte einschließlich L/R, Spektrum und Hüllkurven liegen ausschließlich im privaten Besitzerpaket, nachprüfbar über dessen Datei-/SHA-256-Manifest.

## Offen verbleibende Clipping-Fälle

Nach beiden beobachteten Eingriffen in der Diagnose verbleiben:

| Bank | Programm/Note/Velocity | Überbereichswerte | Peak vor Sättigung |
|---|---|---:|---:|
| Vintage Dreams | 4 / 99 / 112 | 7 negativ | +0,898222 dBFS |
| Vintage Synth 2001 | 49 / 84 / 112 | 6 negativ | +1,035529 dBFS |

Ihre Ursache ist **noch nicht eindeutig nachgewiesen**. Eine zusätzliche, durch Originalregister motivierte Schnellattack-Gegenprobe beseitigt die drei zuvor untersuchten Vintage-Synth-Restfälle nicht; sie wurde ausdrücklich **nicht** als Clipping-Korrektur akzeptiert. Weitere Pegelabsenkung, Limiter oder Filteränderung wären unbelegt und wurden nicht vorgenommen.

Original- und native Beobachtung benutzen unterschiedliche 86Box-DSP-Revisionen. Register- und Sample-DMA-Abweichungen sind davon unabhängig nachgewiesen; die gesamte verbleibende akustische Differenz darf daraus nicht automatisch einem einzelnen DSP-Baustein zugeschrieben werden. Eine physische AWE-Aufnahme dieser vier Banken fehlt.

## Tatsächlich korrigierte Diagnose-/Testfehler

1. **`3cab2d7610d3ac9e0e82d8b05f061c2f3aaca76f`: P228/P229-DC-Auswertung.** `double(88200*2*32768)` überlief schon vor dem Cast. Nenner alt 1.485.307.904, korrekt 5.780.275.200; alte DC-Werte Faktor 3,891634 falsch. Halbpegel-Gegenprobe und alter/neuer echter Bankfall bestätigen: nur DC-Spalten ändern sich. Rail-/Clippingzahlen bleiben gleich. Optionaler privater P229-PCM-/Registerexport ergänzt, vorhandene CLI unverändert nutzbar.
2. **`117d161`: P83-ROM-Sample-Prüfung.** Das gültige Vintage-Dreams-ROM-Sample bei 430.271–430.410 referenziert die 1-MiB-Wave-ROM, nicht `smpl`. Falsche Ablehnung behoben; sechs Tests einschließlich Entfernen des ROM-Bits und Überschreiten der ROM-Grenze bestehen. Kein Sample umgeschrieben.
3. **`c34c644`: Engine-Safety-Test-ABI.** Der Test band die 125A-Bibliothek gegen die veraltete upstream-`Emu8000Box`-Klassendeklaration ein; aktuelle private Felder fehlen dort. Reproduzierter Linux-Segfault, unverändert auch mit größerem Stack. Ausschließlich der Test inkludiert jetzt den tatsächlich gelinkten Adapterheader; derselbe bestehende Test besteht. Keine Änderung an Engine oder upstream.
4. **`ca68572c4fee0693e6e21ab59d0417dc46196e34`: veraltete Sustain-Testannahmen.** Frühere Sollwerte widersprachen bereits belegtem Original-Creative-Verhalten: Generator 37 mit 127→111 und 960→6. Die bestehende Auswahlprüfung verwendet jetzt diese ursprünglichen Treibermesswerte statt 960→0. Grundlage: [unabhängige Original-28er-Serie](CREATIVE-WIN95-28-GENERATOR-HOLD-SUSTAIN-ORIGINAL.md), Original-Lauf [#42904061108](https://github.com/challanger2000/125A-Engineering/actions/runs/42904061108). Kein Produkt-Sustain verändert.

Die zuerst roten Läufe werden nicht verschwiegen: Linux 39/41, Windows [#43026006819](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/43026006819) 48/49. Nach Korrektur der Testfehler:

- **Windows-2022**, exakter Commit `ca68572c4fee0693e6e21ab59d0417dc46196e34`: bestehender Engine-Safety-Workflow [#43028856058 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/43028856058), vollständiger Build und **49/49 CTests**, 206,65 s. [CTests-Rohlog](../qa/p229-independent-20261111/windows-fixed-ctest.log). Diese CI enthält keine privaten Besitzer-SF2s und beweist keine Windows-VST3-Klangidentität.
- **Linux/Debian 13**, Produktkern `8d2f41d` plus dieselben sechs Diagnose-/Testdateien aus `ca68572`, uninstrumentierte separate Quellkopie: **41/41 CTests**, 216,29 s. Die acht zusätzlichen Windows-Tests gehören zur dort eingeschalteten OPL3-Konfiguration. [Rohlog](../qa/p229-independent-20261111/native-fixed-regression-ctest.log).
- P83: **6/6** Positiv-/Negativtests; P228/P229-Parser-/DC-Gegenproben und Ablehnung vorhandener/leerer Mitschnittverzeichnisse geprüft. Tatsächliche Originalmedien wurden ausschließlich lokal verarbeitet.

## Übergabe an den Entwickler und Grenzen

Die nachgewiesenen Produktbefunde liegen in `Synth::LoadBank()` und im SF2-Initialdämpfungs-/VXD-Zahlenformat. **Diese gemeinsamen Engine-Dateien sind unverändert.** Vor einer Umsetzung muss der Entwickler diese Messwerte und die offenen Randbedingungen übernehmen: SF2-Upload inklusive Null-/Randbehandlung, direkte VXD-Dämpfung mit breiterem Controller-/Generator-Nachweis, getrennte Layerauswahl und die beiden verbleibenden Übersteuerungen. Keine automatische Übernahme der archivierten Diagnoseeingriffe als Produktpatch.

Die aggregierten Ergebnisse, SHA-256-Manifest und ausschließlich auf vorhandenen Prüfern beruhenden Reproduktionsadapter stehen in [qa/p229-independent-20261111](../qa/p229-independent-20261111/README.md). Das getrennte private Besitzerpaket enthält die vollständigen 3.082-/234er-Ergebnismatrizen und numerischen Audio-/Register-Einzelfallbelege. Keine neue CMake-Testsuite, CI-Infrastruktur oder VM-Implementierung angelegt. ROM, originale SF2s, Betriebssystem-/Treiberdateien, rohe Sample-RAM-Dumps, PCM und die privaten Einzelfallmatrizen bleiben außerhalb von Git.

**Abnahme:** Diagnose-/Testregression PASS wie oben; nachgewiesene Produktkompatibilitätsfehler **OFFEN**. Vollständige Fehlerbehebung, physische EMU8000-Parität, tatsächliche Windows-VST3-/DAW-Besitzerbank-Audioabnahme, Validator/GUI dieses Auftrags und Release **NOT RUN / BLOCKED**. Keine FULL-AUDIT- oder Releasefreigabe.
