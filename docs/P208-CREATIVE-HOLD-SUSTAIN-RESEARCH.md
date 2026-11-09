# P208 – Hypothesentest: originale Creative-Win95-EG1-Hold/Sustain-Umrechnung

**RESEARCH ONLY:** Produktiver 125A-Windows-VST3 bleibt unverändert. Option AWE125_P208_SF2_HOLD_SUSTAIN ist standardmäßig OFF und bei VST3-Builds ausdrücklich verboten.

## Ausgangspunkt

Original Creative SBAWE.VXD unter Windows 95 in 86Box: echter Registervergleich P207, GitHub Actions 42705889086. Öffentliche SoundFont Spec Test v3.0: Bank0, Programm0, Note59, Velocity100, SampleID43, holdModEnv=0 Timecents und sustainModEnv=500.

Von 32 Registerserien stimmen 29 bereits exakt. Unterschiede: ATKHLD Original 740C / native 750C; DCYSUS Original 4027 8027 / native 3F27 8027; IP Original E1A6 / native E1A7. Dagegen ENVVAL 7A48 und PEFE 7F00 identisch.

## Forschungsannahmen – nicht bewiesene Treiberformeln

- EG1-Hold: Originaler VXD-SF2-Delay-Algorithmus erzeugt bei Timecents 0 genau 1464 Schritte zu 725 Mikrosekunden = 1061.4ms. Würde Hold dieselbe Zeitquantisierung nutzen, ergäbe Ganzzahldivision durch 92ms den Hold-Code 0x74. Bisher: mathematisch exakte 1000ms ergeben 0x75.
- EG1-Sustain: Trunkierung von 500*127/1000 = 63 statt Rundung auf 64 erklärt 0x40 statt 0x3F.
- IP: die +1 Code-Einheit bleibt absichtlich offen. An ihr wird nicht angepasst.

## Abnahme und Grenzen

Native 86Box-SF2-Vergleich von Standardquelle gegen P208-Variant, 47 echte Port-Writes je Note, 32 Registerserien, Daten von originalem Creative-P207-Trace. Negativkontrollen fordern, dass falsche Original-Register erkannt werden. Zwei Sekunden frühe Modulation inklusive Attack müssen in beiden tatsächlich gerenderten WAVs PCM-bitgleich bleiben. Damit sind Hold/Sustain-Treiberunterschiede nicht als Lösung der 81,85-Cent-Hardware-Attackabweichung auszugeben.

P207-Originaltreiber wird nicht neu ausgeführt, sondern seine eingefrorenen numerischen Resultate gelten als unabhängige Referenz. Weitere Generator-Sweeps und originale Win95-VXD-Demontage sind notwendig, bevor die Kandidatenformeln allgemein gelten. Kein realer AWE64-Chip, kein vollumfänglicher Klangbeweis, kein FULL AUDIT, kein Release.
