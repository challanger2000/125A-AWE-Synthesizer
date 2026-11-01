# P21 — SF2 Preset-/Instrument-Gens korrekt kombinieren

**Auslöser:** Nutzer meldet, dass sowohl Bank 0/Programm 7 (`TX81Z Lately Bass`) als auch Bank 0/Programm 0 (`Grungy Ramp Bass`) einer `Synth 512 Bank.sf2` völlig anders klingen, als erwartet.

## Direkte Analyse der Benutzer-SF2

Die *lokal eingereichte* Originaldatei wurde offline nur gelesen und bleibt privat. **Nicht in GitHub übertragen oder weiterveröffentlichen.**

- Datei: SoundFont 2.1 RIFF, 555.754 Byte (ca. 543 KiB).
- 77 verwendbare Presets, 95 Instrumente, 83 verwendbare Sample-Header, 260.921 PCM-Samplewörter (~510 KiB).
- Bank 0/Programm 0: `Grungy Ramp Bass`, zwei Sägezahn-Layer aus `SAWTOOTH` mit `Saw_a1`. Die Preset-Globalzone verändert u. a. Attack, Modulationshüllkurven und Chorus.
- Bank 0/Programm 7: `TX81Z Lately Bass`, vier Layer aus Instrument `ELECTRIC BASS1` mit kurzem Sample `W8_1`. Preset-Zonen verändern Filter, Envelope, Chorus, Detuning und z. T. Coarse Tune.
- Die Datei hat echte eigene Sampledaten und ist viel kleiner als die konfigurierte EMU8000-RAM-Grenze. Die P20-Behandlung fehlgeschlagener SF2-Importe bleibt sinnvoll, erklärt aber allein nicht, warum diese mehreren Klänge bei erfolgreichem Laden falsch klingen.

## Konkreter Quellcodefehler

Bisher verwendete `SelectRegionsImpl` für **alle SoundFont-Versionen**:

```cpp
r.gen.FillFrom(presetGen);
```

`FillFrom` übernahm einen Preset-Generator nur, wenn der Instrumenten-Generator **nicht vorhanden** war. Dieser Ablauf ist für historisch nachgemessene SF1-/SBK-Treiberfälle absichtlich vorgesehen, widerspricht aber der SF2-2.x-Struktur: Die Preset-Werte sind **relative Offsets** zu den Instrumentenwerten.

Beispiel aus Programm 7:
- Instrument `initialFilterQ=100`; Preset `initialFilterQ=-110`. Die bisherige Engine nutzte 100, statt die Summe -10 vor der gültigen Registerbegrenzung zu verwenden.
- Instrument `chorusEffectsSend=0`; Preset `chorusEffectsSend=400`. Bisheriger Klang: Chorus 0, die Preset-Anweisung ging verloren.
- Instrument `attackVolEnv=-7973`; Preset `attackVolEnv=-3986`. Bisher -7973 statt kombinierter -11959.
- Instrument `fineTune=-5`; Preset `fineTune=-1`. Bisher -5 statt -6.

Auch Programm 0 hatte in beiden Sägezahn-Layern `chorus=0` auf Instrumentenebene und `chorus=500` in der Preset-Zone, das zuvor ignoriert wurde.

## P21 Korrektur

- Für **SoundFont::Version::Sf2** wird jetzt `GenSet::AddFrom` verwendet (relative Preset-Offsets).
- Für **SoundFont::Version::Sf1** bleibt `GenSet::FillFrom` unverändert (gemessene alte Creative-Treiberlogik).
- Struktur-Generatoren `Instrument`, `SampleID`, `KeyRange`, `VelRange` werden nicht addiert.
- 16-bit-Summen werden saturiert, kein Integer-Wrap bei malformed/untrusted SF2.
- Regressions-CTest stellt SF2-Filter, Chorus, Attack/Decay/Release, FineTune und SF1-Precedence mit synthetischen Daten nach; ein generierter SF2-Audiotest enthält nun bewusst dieselben Generatoren auf Instrument- und Preset-Ebene.
- Keine Benutzer-SF2 im öffentlichen Repository; keine Änderung an P20-Fehleranzeige, FM-Engines, GUI oder VST3-Parameter-IDs.

## Aussagegrenzen

**CI-Status: WINDOWS-PASS.** Selbst wenn alle automatischen Tests bestehen, ist damit die Klanggleichheit zu einer originalen Sound-Blaster-AWE32-Hardware oder zu einem echten Yamaha TX81Z nicht erwiesen. Ein SoundFont-Preset mit dem Namen TX81Z ist eine EMU8000-Samplekonstruktion und keine native TX81Z-4-OP-FM-Emulation. Ein Vergleich mit einer Referenz-SoundFont-Wiedergabe ist für die finale akustische Abnahme sinnvoll.

## Windows-Nachweise (2026-11-01)

- P21 getestet mit Source `40a943bb3912cd22c6e496b7fe323fa4812b871c`.
- [P21 VST3 Actions #41273754442](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41273754442): **SUCCESS**, 16/16 CTests, 47/47 Steinberg Validator, Win32 EditorHost GUI PASS.
- [P21 Native #41273754415](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41273754415): **SUCCESS**, 14/14.
- P22 baut auf P21 auf und korrigiert außerdem die SF2-Sustain-Standardwerte; aktueller Stand in `docs/P22-SF2-SUSTAIN-SEMANTICS.md`.
- Originale Benutzer-SF2 wurde **nicht** in GitHub eingecheckt. Realer akustischer Vergleich 125A gegen FluidSynth/EMU8000 unter Studio One bleibt NOT RUN.
