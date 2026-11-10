# P222 – Kausal getrennter Reverb/Chorus-A/B-Test (VST3, private SoundFont)

**Gegenstand:** Analyse der nachgewiesenen 59/77 beim alten P220-ModFX-VST3-Recorder bis zum digitalen vollen Sample-Wert ausgesteuerten Programmdurchgänge. Forschungsstand **10.11.2026**. Die produktive DSP-Implementierung ist **unverändert**; es gibt **keinen Klang-PASS und keine Releasefreigabe**.

## Gesicherte Vorgeschichte (kein Kausalbeweis)

Benutzereigene `Synth 512 Bank.sf2` (555.754 Byte, SHA-256 `d5b99ec38fddf59f53f66b90921e170d207bf3bbd73960f6e4175c39ef68349b`) sowie das vom Nutzer bereitgestellte `P220-PRIVATE-VST3-WAV.zip`: 77 DRY-Aufnahmen ohne im Recorder gemeldete Fullscale-Übersteuerung, 59/77 MODFX-Aufnahmen mit voller digitaler Aussteuerung (112.143 Werte −1 und 50.100 Werte +32767/32768 über die 59 fehlerhaften Aufnahmen). Aus den alten Paaren ist eine reine Effektursache **nicht** ableitbar: DRY war Note48/Velocity64/CC1=0 und GUI-Effekte 0, MODFX dagegen Note72/Velocity120/CC1=96 und beide GUI-FX=100%.

Wichtig: Die als `FAILED-UNCLIPPED-F32.wav` bezeichneten Float-Aufnahmen waren bereits auf exakte 1/32768-Schritte quantisiert und max. −1 bzw. +32767/32768. Ein Export in WAV FLOAT32 rekonstruiert **keine** zuvor im EMU8000-/Plugin-Pfad gesättigten Amplituden.

Quellcodebestätigung: `FxSendLevel::Apply(base,1.0f)=255` (`src/engine/FxSendLevel.h`); damit überschreiben die 100%-GUI-Sends die aus SF2/CC91/CC93 berechneten Basis-Sends. Deshalb kann der alte MODFX-Test nicht als original-Creative-treibergleich gelten, auch wenn CC91=48/CC93=32 gesendet wurden.

Die Originalbank wurde privat **nur anhand ihrer Strukturdaten** untersucht, nicht auf GitHub veröffentlicht:
- **Programm 000, Grungy Ramp Bass:** zwei leicht unterschiedlich gestimmte Zonen (±5 Cent); bei Note48 und Note72 werden verschiedene Original-Sample-IDs aus verschiedenen Key-Zonen verwendet. Globaler SF2-Chorus-Send = 500, Reverb-Send = 20 (SF2-Zehntel-Prozent-Angaben).
- **Programm 021, Wailing Hit:** zwei hart links/rechts gepannte Zonen mit derselben Sample-ID; globaler SF2-Chorus-Send = 300. Das war mit 46.485 negativen Fullscale-Samples der stärkste Effekt-Aussteuerungsfall. Diese Struktur ist ein geeigneter Stresstest, **kein** Beweis, dass Layering die Übersteuerung verursacht.

## P222: Minimaler kontrollierter Faktorversuch statt nochmals 77×2

Die bestehende, unter Windows bereits erfolgreiche **P171/P220 VST3-Host- und WAV-Recorder-Implementierung** wird im Forschungsbranch `qa/p222-controlled-fx-factorial` nur für diesen A/B-Test erweitert.

| Faktor | Geprüfte Werte |
| --- | --- |
| MIDI-Preset | Exakte Nummer 000 und 021 der privaten Bank |
| Note/Velocity, je getrennte Vierergruppe | 48/64 und 72/120 |
| In jeder Vierergruppe **immer identische** MIDI-Controller | CC1=96, CC7=100, CC11=127, CC91=48, CC93=32 |
| **Einzig variierte unabhängige Eingangsgröße** innerhalb der Vierergruppe | GUI-Effektsend Reverb/Chorus = `0/0` (DRY), `10000/0` (REVERB), `0/10000` (CHORUS), `10000/10000` (BOTH) |
| MIDI-Timing | NoteOn bei Frame0, NoteOff bei Frame44.100, Messung 132.300 Frames / 3,0 Sekunden |
| Audio | Originale 44.1k-Stereo-Windows-VST3-`process()`-Samples, pro Fall zusätzlich **WAV IEEE-Float32**, nicht nachträglich normalisiert; PCM16 nur ohne Fullscale-Werte |
| Prüfpunkte | Quantisierung auf 16-Bit-Werteraster, positiver und negativer Digital-Rail, RMS, absoluter Peak, Differenz zur DRY-Aufnahme, erstes Clip-Frame, Anzahl PCM-Callbacks |
| Vollständiger Versuch | 2 Programme × 2 feste Note/Velocity-Kombinationen × 4 Effektzustände = **16** WAV-Vergleiche (je eine zusätzliche Float-Datei) |
| Separater öffentlicher CI-Test | Ein einziger synthetischer Preset-0-Sound mit 2 Note/Velocity-Paaren × 4 FX-Zuständen = 8 **echte VST3-`process()`-Outputs**, ausdrücklich **nicht** der privaten SoundFont |

Die Benennung `P000-N72V120-REVERB-ACTUAL-VST3-F32.wav` sagt genau aus, was sie enthält: **Originalwerte des exportierten VST3-`process()`-Callbacks, auch wenn bereits vor dem Callback im Plugin digital gesättigt**. Sie darf NICHT als entclipte Hardware-/Creative-WAV verstanden werden.

**Kritischer Fix am Test-Orakel:** Die +16-Bit-Fullscale-Probe `+32767/32768` liegt numerisch unter der zuvor einzigen Clip-Schwelle `0,99997` und konnte deshalb fälschlich passieren. P222 zählt **beide** 16-Bit-Grenzwerte getrennt; der zusätzliche adver­sariale Test `--self-test-positive-rail` muss einen solchen positiven Clip als solchen erkennen. Für echtes Nachschwingen/physische AWE64 ist dieser Test noch keine Aussage.

## Auswertung

`tools/p222_analyze_fixed_fx_ab.py` prüft die vollständigen 16 verifizierten Float-WAV-Dateien samt VST3-Recorder-Protokoll, festem Controller-/GUI-Zustand und **exaktem SHA-256 der privaten Originalbank**. Für eine rein synthetische CI-Gegenprobe existiert ein klar beschrifteter Modus `--synthetic-probe`, der **kein** Originalbank-Zertifikat erzeugen darf. Erfasst werden pro Preset/Note/Velocity die tatsächlichen Rail-Muster für DRY, nur Reverb, nur Chorus und beide, jeweils mit RMS-/Differenzwerten.

**Interpretationsgrenzen:**
- Ist bei identischer Note/Velocity **schon DRY** am digitalen 16-Bit-Grenzwert, liegt die Ursache nicht **ausschließlich** an den Effekt-Returns.
- Bleibt DRY ohne Rail, eine einzeln aktivierte FX-Stufe erreicht aber einen Rail, ist **für genau diese festen MIDI-/GUI-Eingaben** eine effektabhängige Aussteuerung gezeigt. Ob das ein musikalisch falsches Gain-Verhalten oder die gemessene volle Send-Kurve ist, erfordert danach Original-Creative-Ausgangsdaten.
- Wenn nur BOTH railt, liegt eine **Kombinationsübersteuerung** nahe; ein vollständiger Frequenz-/Timing-/FX-Audit bleibt trotzdem gesondert erforderlich.
- Weder gleiche MIDI-CCs bei absolut unterschiedlichen GUI-Send-Kurven noch eine reine 86Box-Wellenform beweisen **physische Creative-Hardware-Gleichheit**. Das originale Creative-Win95-Audio deiner privaten Bank ist weiterhin nicht aufgenommen.

## Reproduzierbarkeit und Übergabe

- Forschungsbranch: [P222](https://github.com/challanger2000/125A-AWE-Synthesizer/tree/qa/p222-controlled-fx-factorial)
- `tests/p220_77_vst3_pcm_recorder.cpp`: erweiterter **bereits vorhandener** P171-basierter Windows-Recorder, neue Modi `fx-factorial`, `fx-factorial-probe`; alter P220-Pfad bleibt erhalten.
- `tools/P222-LOCAL-FX-AB.bat`: benötigt nur die zugehörigen Windows-EXE-/VST3-Build-Bestandteile und lokale Pfade für ROM/SF2, keine VM, kein Python, keine Installation; schreibt 16 private Float-WAVs und ein Log in einen neuen, nicht überschriebenen Ordner.
- `tools/p222_analyze_fixed_fx_ab.py`: unabhängiger messwertbasierter Auswerter. Er muss nicht vom Nutzer lokal installiert werden; Auswertung kann nach Übermittlung des privaten Diagnosepakets erfolgen.
- CI: [Aktuelle P222-Actions-Runs](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/workflows/p220-real-windows-vst3-recorder.yml) (Grün ist nur Testprogramm und synthetische Negativmutation, keine Originalbank-Klangtreue).
- **Keine Änderung der eigentlichen VST3-Klangerzeugung; kein Merge und keine Releasefreigabe.**

## Verbindliche noch offene Nachweise

**16 originale Nutzerbank-VST3-Faktoraufnahmen:** noch nicht ausgeführt. **Creative Windows 95:** 154 eigene Bank-Tonaufnahmen fehlen weiterhin, inklusive Nachweis tatsächlich geladener Samples. **Original-Creative- vs. VST3-Klangtreue:** **0/77 PASS**, weiterhin `BLOCKED`; echte AWE64-Hardware, Studio One/ASIO und flächendeckende ADSR-/Filter-/Loop-/Effektabnahme weiterhin `NOT TESTED`.
