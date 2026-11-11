# P235 — Original Creative dry PCM versus native Filter × Interpolation (2026-11-11)

**Freigabe:** Vier temporäre Diagnose-Builds A Chamberlin+B-Spline4 (aktueller Stand), B Chamberlin+Cubic, C 86Box-Moog+B-Spline4, D 86Box-Moog+Cubic. **Keine Änderung an der produktiven Engine**, keine neuen Branches, kein Merge.

**Reproduzierbare Original-Evidenz:** [Private GitHub Actions #42999169354](https://github.com/challanger2000/125A-Engineering/actions/runs/42999169354), numerisches [Artefakt #13845838532](https://github.com/challanger2000/125A-Engineering/actions/runs/42999169354/artifacts/13845838532), Datei `P235-filter-interpolation-fourway-original-Creative-dry.json`, Roh-Audio privat und nach Messung gelöscht. Test-Produktquellstand `b0a3143f20c3ea90511b5e3f560f49b189be5709`; Original-86Box `b7b24d4b82c72aa49c4f7a55e2ed53026d214293`; privater Workflow `807d60b10680bfd6e49cd2af80672209aee990c5`.

ROM SHA-256 `4e143b94f758734f594ded78f4e5115635975c16fa37fabeae0baa4938ca710e`, Original-Creative `SYNTHGM.SBK` SHA-256 `fd2e35a260fef22fe809918dda3c921c6d48d53a29c3515af8a41019ce72d586`. Original-Win95-Creative/EMU8000-Provenienz bestanden, **ein gemeinsamer neu aufgenommener Original-Dry-PCM-Satz je GM** für alle vier Varianten. Original- und Native-Dry-Abgriff jeweils **vor Reverb, Chorus und Ausgangs-EQ** (keine Lautstärkennormalisierung). P234 tatsächliche Register-NoteOff-Dauer **12/12 PASS** (GM0 Original 44099/Native 44100 Samples, GM39 44100/44100, GM88 44096/44100; Grenzwert ±44), **Registertraces zwischen A/B/C/D bei 3/3 GM exakt gleich**.

## Hauptvergleich: Pre-NoteOff-RMS (Original minus 125A, dB)

| GM | A Chamberlin+B-Spline4 | B Chamberlin+Cubic | C Moog+B-Spline4 | D Moog+Cubic |
|---|---:|---:|---:|---:|
| 0 | −0,046 | −0,102 | +0,081 | **+0,025** |
| 39 | −4,383 | −4,413 | **−0,012** | −0,049 |
| 88 | +0,149 | −0,156 | +0,314 | **+0,012** |

**Isolierte Faktorwirkung auf Native-RMS, vor NoteOff:** GM0 Moog minus Chamberlin −0,127 dB (unabhängig von Interpolator), Cubic minus B-Spline4 +0,056 dB (unabhängig vom Filter). GM39 Filter −4,371/−4,364 dB mit B-Spline/Cubic, Interpolation +0,030/+0,037 dB; Wechselwirkung nur +0,007 dB. GM88 Filter −0,165/−0,168 dB, Cubic +0,305/+0,302 dB; Wechselwirkung −0,003 dB.

## Vor NoteOff: Spektrum, Peak und Hüllkurve (nicht normalisiert)

| GM | 4–10 kHz Original−A | Original−D | 10–20 kHz Original−A | Original−D | Hüllkurvenkorrelation A / D | Original- / D-Peak dBFS |
|---|---:|---:|---:|---:|---:|---:|
| 0 | +11,703 dB | **+0,004 dB** | +0,762 dB | −0,083 dB | 0,99999 / 0,99999 | −37,579 / −37,579 |
| 39 | +7,888 dB | **+0,052 dB** | −13,915 dB | −0,029 dB | **0,90577 / 0,99488** | −28,639 / −27,997 |
| 88 | +8,681 dB | **+0,346 dB** | +8,292 dB | +0,317 dB | 0,99761 / 0,99807 | −27,325 / −27,160 |

**Interpretation:** Die starke GM39-Dry-Pegelabweichung wird vom Filteralgorithmus und nicht vom Interpolator dominiert. Der Interpolator wirkt besonders auf den Hochtonanteil: die Variante D (Moog+Cubic) stimmt in diesem Drei-GM-Test in fast allen analysierten Spektralbändern wesentlich besser mit der originalen Creative/86Box-Dry-Referenz überein. **D ist trotz dessen KEIN nachgewiesen bitidentisches vollständiges AWE64-/VST3-Produkt**.

**Nach NoteOff Original−Native RMS (A / D):** GM0 +0,264 / +0,311 dB; GM39 −4,161 / +0,251 dB; GM88 +0,364 / +0,143 dB. GM39 Hüllkurvenkorrelation nach NoteOff 0,99972 / 0,99998; die getrennte Onset-Hüllkurve GM39 verbessert sich von **−0,54267 (A)** auf **+0,98624 (D)**.

## GM39: tatsächlich getrennt gemessene physische Chipstimmen 0 und 3

Die originale Win95-Treiber-Registerspur und 125A ordnen beide GM39-NoteOns nachweislich **physischen Stimmen 0 und 3** zu. In der privaten P235-Messung wurden deren tatsächliche PCM-Beiträge separat unmittelbar nach Voice-Filter/Gain, vor FX abgegriffen. Beide individuellen Referenzen und Native-Stimmen hatten gültige aktive PCM-Signale.

| Variante | Stimme 0 Original−Native RMS vor NoteOff | Stimme 3 Original−Native RMS vor NoteOff | Stimme 3 Hüllkurvenkorrelation vor NoteOff |
|---|---:|---:|---:|
| A | −0,185 | **−8,093** | 0,80048 |
| B | −0,197 | **−8,123** | 0,80064 |
| C | +0,075 | +0,138 | 0,99863 |
| D | +0,063 | **+0,062** | **0,99855** |

**Ursachenbewertung:** Die starke GM39-Abweichung stammt maßgeblich aus der Filterverarbeitung von Stimme 3. Der identische Registerstrom aller A–D-Varianten schließt eine durch die Varianten geänderte Creative-Treiberübersetzung als Ursache dieses Faktorvergleichs aus.

## Weiterhin offener Stimmenstart

Gemessene erste ungleich Null liegende PCM-Samples **relativ zu tatsächlichem NoteOn** (Original / D): GM0 **11 / 15** (−4 Samples), GM39 **5 / 20** (−15 Samples), GM88 **0 / 108** (−108 Samples). Bei GM39 stimmen die Hüllkurven im weiteren Verlauf besser überein, jedoch beginnen native Stimmen **0 und 3** bei D um etwa **34 beziehungsweise 15 Samples später** als die originalen Stimmen. Das ist ein eigenständiger, **noch nicht aufgeklärter Start-/Latenzunterschied** und darf nicht per manuellem WAV-Shifting oder pauschaler Gainkorrektur versteckt werden.

## Gate / Freigabe

- Vier neue, **temporäre** native A/B/C/D-Builds mit reellen Original-Treiberdaten: **12/12 P234-Timing**, 3/3 identische Variant-Registertraces, 12 tatsächliche Dry-Audiopaarmessungen und GM39-Stimmenpaare.
- Originaler FX-Rückweg nicht Gegenstand dieses Dry-Versuchs. **Produkt-DSP und hardwarekalibrierte Algorithmen unverändert**, kein Merge, kein Branch, kein Release.
- **3 Creative-Original-Drum-WAVs weiterhin invalid/blockiert**; deshalb meldet der abschließende P231-Fail-Closed-Gate den CI-Gesamtlauf bewusst als rot, obwohl der P235-Diagnoseschritt erfolgreich abgeschlossen wurde.
- **Nächster sinnvoller begrenzter Schritt:** den nach dem Interpolations-/Filter-Faktorvergleich verbleibenden **Stimmenstartversatz pro physischer Stimme** anhand von Sample-Startadresse, CCCA-Leseposition, Attack-Trigger und 86Box-Update-Latenz aufklären, dann gemeinsamen Code nur nach unabhängiger Gegenprüfung zur Freigabe vorschlagen. Vorher keine Produktionsänderung.
