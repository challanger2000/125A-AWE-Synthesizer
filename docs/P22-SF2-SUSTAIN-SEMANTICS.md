# P22 – SoundFont-2-Sustain-Standardwerte und Modulations-Sustain

**Status: Code und Regressionen implementiert, Windows-Build/Validator noch nicht ausgeführt.**

## Mit hochgeladener SF2 nachgewiesener Fehler

Die privat hochgeladene `Synth 512 Bank.sf2` enthält in **Bank 0/Programm 000 – Grungy Ramp Bass** weder auf Preset- noch auf Instrumentenebene einen `sustainVolEnv`-Generator. Sie ist ein gültiger SoundFont 2.x. Der SF2-2.04-Standard definiert für einen fehlenden `sustainVolEnv` den Defaultwert **0 centibel Attenuation**, entsprechend **volle Sustain-Lautstärke**; ebenso ist der Default des Modulations-Sustain-Generators **0 Promille Attenuation**, entsprechend vollem Modulations-Sustain.

Der bisherige `SoundFont::MakeVoiceParams`-Code benutzte für **beide** Formate einen gemeinsamen Wert `0` als Hardware-Register (vollständiges Abklingen). Bei SF1/SBK war dies absichtlich aus Treibertraces abgeleitet. Bei SF2 ist es nachweislich falsch und beeinflusst auch Programm 000.

Außerdem behandelte die bisherige Konvertierung `sustainModEnv` (0..1000 Promille) genau wie `sustainVolEnv` (0.1-dB-Einheiten), obwohl die Einheiten laut SF2-Spezifikation verschieden sind.

Referenz: [SoundFont Technical Specification 2.04, Generator-Tabelle S. 38](https://musescore.org/sites/musescore.org/files/2023-01/sfspec24.pdf#page=38).

## Korrektur

- `SoundFont::Version::Sf2`: fehlendes `sustainVolEnv` bzw. `sustainModEnv` ergibt den EMU8000-Registerpegel **127** (maximales Sustain).
- `SoundFont::Version::Sf1`: fehlender Sustain-Wert ergibt wie zuvor Register **0**. Bewährte DOS-/Win95-Tests bleiben unverändert.
- Explizites SF2 `sustainVolEnv`: dB-Attenuation bleibt in der bestehenden Umrechnung (0.75 dB/EMU8000-Sustain-Schritt).
- Explizites SF2 `sustainModEnv`: Absenkung in 0.1-Prozentpunkten wird korrekt auf den linearen 0..127-Regler abgebildet.
- Ein explizites `sustainVolEnv=960` (wie in einigen Zonen des hochgeladenen `TX81Z Lately Bass`) bleibt **nahe Null**, es wird also nicht durch den fehlenden-Generator-Default ersetzt.
- Keine Dateien/Samples aus der privaten SF2 in das öffentliche Repository kopiert.

## Regressionsbelege

- Generierter SF2-Bass ohne Sustain-Gens: erwartet `DCYSUSV[14:8]=0x7F` und `DCYSUS[14:8]=0x7F`.
- Explizit `sustainVolEnv=120 cB`: 12 dB, EMU8000 Sustain **111**; `sustainModEnv=600` (60 % Attenuation): Sustain **51**.
- Explizit `sustainVolEnv=960` und `sustainModEnv=1000`: Sustain **0**.
- Historisch kompatible SF1-Testbank ohne Sustain-Generatoren: Sustain **0** wie vor P22.
- P21-Offset- und Synthese-Audiotests sowie GUI-Hosttest bleiben Pflicht.

**Grenze:** Ein Name wie `TX81Z Lately Bass` in SF2 bedeutet eine samplebasierte EMU8000-Klangprogrammierung, keine native Yamaha-TX81Z-FM-Emulation. Vollständig identische Klänge zu einer Referenzengine bzw. Originalhardware sind nicht durch dieses isolierte Sustain-Testpaket nachgewiesen.
