# P217 – Original-Creative-SF2-Filterregister-Audit (Cutoff, Q, EG1 und LFO)

## Ziel, Baseline und Abgrenzung

Den **aktuell vollständig unter Windows geprüften Produkt-Soundcode P216** (`50dbd6713736b9c60bb33a3a5c737e57b926fd64`) gegen den originalen Windows-95-Treiber von Creative für die vier wichtigsten Filtergeneratoren abnehmen. **Keine DSP-Änderungen, kein Merge, kein Release.** Das alte P216-28/28-Ergebnis betrifft ausschließlich EG1-Sustain und ist kein Beleg für diese vier Filterparameter.

1. Original Creative 1998 `SBAWE.VXD`, SHA-256 `d343f2428ab3e593c9e42a668cf521b7801e1239792eaf7f2b11b5f179bc7c9a`, Win95 WinMM, 86Box AWE64 Gold 28 MiB. [Originaltreiber-Workflow P217 #42746189039](https://github.com/challanger2000/125A-Engineering/actions/runs/42746189039). Echte Registerfenster, kein modellierter Sollwert.
2. Original Creative-accepted SoundFont v3.0, Git-Blob `4768c4a0215abf49c7a2bb51ada5ba3494faa1c5`. Unverändert: alle sechs Original-Presets, 25 Original-Instrumente, 44 Sample-Header und der gesamte Audiodaten-/INFO-Bereich. Genau 28 abgeleitete zusätzliche Presets, Programme 100–127, mit genau **einem** variierten Filtergenerator pro Programm. SF2 SHA-256 `89792cb61712c1a33a5bead1ff4318005e293dbfd1443ac148c3a46d85ff0b61`.
3. Native Produktquelle P216 unverändert, separat kompiliert und mit dem gleichen SoundFont über den tatsächlichen 86Box-EMU8000-Chip mit identischer Note59/Velocity100 abgespielt. [P217 nativer Messlauf #42746361698](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42746361698), Artefakt `P217-real-native-P216-EMU8000-28-filter-register-records`.
4. [Quellbank-/adversariale Parserprüfungen #42745865150](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42745865150); [verschärfte Registervergleichs-Gegenprüfung #42746980230](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42746980230).

## Versuchsplan

| SF2-Generator | 7 einzeln vorgegebene wirksame Werte | Registerziel |
| --- | --- | --- |
| Cutoff, `initialFilterFc` (8) | 1500, 3500, 5500, 7500, 9500, 11500, 13500 Cents | **IFATN high byte** |
| Resonanz, `initialFilterQ` (9) | 0, 10, 30, 60, 100, 240, 960 cB | **CCCA_HI high nibble** |
| EG1→Filter, `modEnvToFilterFc` (11) | −12000, −6000, −1200, 0, 1200, 6000, 12000 Cents | **PEFE low byte**, signed |
| LFO1→Filter, `modLfoToFilterFc` (10) | −12000, −6000, −1200, 0, 1200, 6000, 12000 Cents | **FMMOD low byte**, signed |

Der Generator konstruierte alle Preset-Generatoren als **additive Deltas zum tatsächlich gemessenen Originalinstrument-Basiswert**, statt einen künstlichen Layer zu erzeugen. Für die authentifizierte Sample43-Note59-Quelle ergaben sich Basen Cutoff 13500, Q 0, EG1-Filter 0, LFO1-Filter 0. Die Originalwerte wurden unabhängig aus dem Original-SF2 gelesen, keine Register-Sollwerte geraten.

### Wichtig: Zwei Schreibvorgänge von `CCCA_HI`

Der P217-native-Registertrace beweist für jeden Ton **zwei CCCA_HI-Schreibvorgänge**. Der erste setzt Q noch auf null; der zweite enthält die tatsächlich programmierte Resonanz. Wer nur das erste Wort auswertet, kann einen völlig falschen `Q=0`-Befund erzeugen. Deshalb archivieren die Belege **jede** Registerschreibfolge und der unabhängige Auswerter `tools/p217_compare_creative_native_filters.py` vergleicht für Q bewusst die **letzte** `CCCA_HI`-Schreiboperation. Ein adversarialer Negativtest verändert ausschließlich dieses letzte Q-Wort und **muss** die Prüfung rot färben. Die bereits aufgezeichneten Rohwerte bleiben unverändert. Die während des originalen Win95-Laufs gepinnte erste Version des Originalerfassungs-Skripts berichtet in ihrer abgeleiteten Q-Kurzspalte noch den ersten Wert; diese Kurzspalte ist **nicht belastbar**. Maßgeblich ist die vollständige originale `CCCA_HI`-Registerliste, aus deren letztem Wort P217 den korrekten Q-Wert errechnet.

## Getrennte Evidenzstufen / Release-Gates

- Tatsächlich geprüfte Original-Creative-**Registersteuerung** ist NICHT dasselbe wie **frequenzabhängige Filterübertragung**, Q-Bandbreite, zeitlich modulierte Frequenzgangkurven, Analogstufe oder physisches Silizium.
- Die ältere physische CT4390-Hardware-Auswertung P193 [#42584492536](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42584492536) fand mediane **Notenpegel**-Fehler von 0,161 dB für Cutoff und 0,490 dB für Resonanz. Das sind keine gemessenen parametrischen Filter-Übertragungsfunktionen und kein Nachweis, dass alle Filterstufen stimmen.
- Noch separat erforderlich: EG1 Delay/Attack/Hold/Decay/Sustain/Release zusammen mit EG1→Filter, LFO-Phasen/Sync/Waveforms, Velocity/Key-Modulatoren, Cutoff und Q in Kombination, Pegel-/Spektralantwort an echter AWE64 Gold und schließlich Studio One mit ASIO.
- Native Win95/86Box-Registervergleich, Original-Creative-Treiberaufzeichnung, physischer Hardware-Audioabgleich, Windows VST3 Test Lab und Endabnahme werden als **verschiedene** Prüfbereiche ausgewiesen.
- Ein erfolgreiches CI-Job-Ende beweist nur die ausgeführten Quellen-/Vollständigkeitsprüfungen; wenn ein tatsächlicher Filterregistervergleich divergiert, bleibt der jeweilige Filterbereich **FAIL**, und die vorherigen Windows-Validator-PASS zählen nicht als Gegenbeweis.

**Status:** Quelle und 28 Programmkonstruktionen unabhängig positiv geprüft; 28 native Registeraufzeichnungen gesichert; originaler Creative-Win95-Lauf **noch ohne verifiziertes Gesamtergebnis**, zu prüfen unter den verlinkten Original-Actions. **Kein Produkt-DSP geändert und keine pauschale Aussage „alle Filter korrekt“.**
