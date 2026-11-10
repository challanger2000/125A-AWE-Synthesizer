# P218 — SF2 negative Filter-LFO darf die Pitch-Tiefe von FMMOD nicht verändern

**Stand:** 2026-11-10. Isolierter Korrekturkandidat, NICHT GEMERGT, keine Studio-One-/ASIO- oder Releasefreigabe.

## Primärquellen und feste Vergleichsgrundlage

- Original Creative Windows 95 (SBAWE.VXD, AWE64 Gold in 86Box, 28 MiB), **28 wirkliche isolierte MIDI-Noten-/EMU8000-Registerfenster**: [Engineering-Actions #42746189039](https://github.com/challanger2000/125A-Engineering/actions/runs/42746189039), Artefakt `13731444381`.
- Ursprünglicher P216-Stand: Commit `50dbd6713736b9c60bb33a3a5c737e57b926fd64`, [nativer 28er-Vergleich #42746361698](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42746361698), Artefakt `13730559162`.
- Korrigierter P218-Stand: Commit `65ffbc909867ee54e2a2819990844fa8e3bf6bc6`, [nativer 28er-Test #42750226234](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42750226234), Artefakt `13732708936`.
- Alle Läufe verwenden dieselbe quellsauber abgeleitete SF2-Testbank: SHA-256 `89792cb61712c1a33a5bead1ff4318005e293dbfd1443ac148c3a46d85ff0b61`; unveränderte 44 SoundFont-Samples, sechs Original-Presets und 25 Original-Instrumente plus 28 additive Presets 100–127. Getestet wird Note 59, Velocity 100, je sieben Werte für die vier SF2-Filtergeneratoren.

## Befund und nachgewiesene Ursache

P216 wendete in `Synth::StartVoice` die frühere allgemeine Win95-Vorzeichenerweiterung des **FMMOD-Filter-LFO-Low-Bytes** auf **alle** Bankformate an. Dadurch wurde bei einem negativen SF2-Filter-LFO-Wert gleichzeitig das **High-Byte der LFO-Pitch-Modulation** auf `0xFF` gesetzt, obwohl der originale Creative-Win95-Treiber bei den kontrollierten SF2-Proben dort `0x00` schrieb:

| SF2 Filter-LFO in Cents | Original Creative | P216 vorher | P218 nachher |
| ---: | --- | --- | --- |
| -12000 | `0x0080` | `0xFF80` | `0x0080` |
| -6000 | `0x0080` | `0xFF80` | `0x0080` |
| -1200 | `0x00D6` | `0xFFD6` | `0x00D6` |

Die einzige produktive Codeänderung konditioniert die bisherige Vorzeichenerweiterung auf `bank->version == SoundFont::Version::Sf1`. **Die SF1-Logik selbst wurde nicht geändert.** Die bisherige alte SF1-Treiberbehauptung ist durch diese SF2-Messung nicht widerlegt; sie wird nicht auf SF2 übertragen. Beide Messungen sind numerische reale Register-Traces, keine künstlich berechneten Sollwerte.

## Unabhängige Nachprüfung

- 28/28 kontrollierte Programme liefen mit **echten nativen P218-EMU8000-Stimmen** durch; Build, zugehöriger P90-Test und der separate Registrierungs-/Provenienztest sind im erfolgreichen [Actions-Lauf #42750226234](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42750226234) enthalten.
- Vergleich von **allen fünf Register-Schreibfolgen** gegen das unverändert archivierte Original-Creative-Artefakt, nicht gegen P218-Code: **P216 18/28**, **P218 21/28** identische Fälle. Die obigen drei P218-FMMOD-Fälle sind vollständig registeridentisch geworden; alle 18 zuvor erfolgreichen Fälle bleiben unverändert erfolgreich.
- **Weiterhin 7/28 FAIL:** Cutoff-Programme `102=38 vs 39`, `104=176 vs 175`, `105=245 vs 243`; Q-Programm `108=0 vs 1`; EG1-Filterprogramme `116=0xEC vs 0xEB`, `119=0x6B vs 0x6A`; LFO-Filterprogramm `125=0x2B vs 0x2A`. Jede Paarangabe ist `original Creative vs P218`.
- Für Q gilt: `CCCA_HI` wird **zweimal** geschrieben. Die endgültige Resonanz steht im **zweiten** Wort; Auswertungen des ersten Wortes sind falsche Tests. Der P217-Komparator enthält einen gegen diesen Fehler gerichteten Negativmutanten.
- **Ausstehend:** zusätzlicher echter SF1-Vorzeichen-Regressionsvektor, alle übrigen Windows-CI-/Test-Lab-Gates, vollständige Creative-SF2-Umrechnungsbereiche, Filter-PCM-/Frequenzgänge, dynamische EG1/LFO-Verläufe und reale Studio-One-ASIO-Abnahme.

## Entscheidung

**P218 gezielte FMMOD-SF2-Registerkorrektur: in 3/3 betroffenen P217-Referenzfällen BESTÄTIGT.**
**Gesamte Filterregistertreue: FAIL (21/28).** Kein Merge und keine Behauptung „alle Filter korrekt“. Die sieben verbleibenden Abweichungen sind anhand originaler Creative-Treiberroutinen oder eines umfassenden originalen Treiber-Sweeps zu klären, nicht durch willkürliche Rundungskonstanten.
