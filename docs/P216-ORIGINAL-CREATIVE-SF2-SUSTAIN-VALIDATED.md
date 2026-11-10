# P216 – Creative Win95 SF2 EG1 Sustain: gezielte Produktkorrektur und Windows-Abnahme

**Befund am 10. November 2026, geprüftes Produkt-Commit: `50dbd6713736b9c60bb33a3a5c737e57b926fd64`**, Branch `fix/p216-original-creative-eg1-sustain`.

**Beide Jobs SUCCESS:** [P216 Originaltreiber-Register-Gate und vollständige Windows-Abnahme #42742531063](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42742531063). **Kein Merge und kein Release.**

## Ursache und Korrektur

Die vorherige Win95-SF2-Implementierung addierte Generator 29 `sustainModEnv` aus Instrument und Preset in SF2-Rohwerten und quantisierte nur einmal mit `lround`. Der originale Creative-Win95-Treiber wandelt beide Generator-Ebenen separat in Registereinheiten um. Dies wurde zunächst mit echtem Original-Win95-Treiber (P213/P214), danach mit getrennten nativen 86Box-EMU8000-Implementierungen (P215) belegt.

- **VxD-Arithmetik:** `T(x) = 127 + trunc_toward_zero((-127*x)/1000)`.
- **Wirksamer Sustainregisterwert:** `clamp(T(instrument_base) + T(preset_offset) - 127, 0, 127)`.
- P216 sichert die beiden Rohkomponenten vor `GenSet::AddFrom` in der flüchtigen `Region`; eine nachträgliche explizite Änderung des bereits zusammengeführten Generators wird erkannt und dann als eigenständiger absoluter Wert mit `T(x)` umgerechnet.
- **Nur zwei produktive Dateien geändert:** `src/engine/SoundFont.h`, `src/engine/SoundFont.cpp`. SF1/SBK, DOS-/Nicht-Win95-Treiber, SustainVolEnv (Generator 37), MIDI, Effektverarbeitung, GUI und gespeicherte Projektparameter bleiben funktional unberührt. Die flüchtige `Region` erhält zusätzliche Felder; es gibt keinen Wechsel des serialisierten Projektformats.
- P216 wurde *gezielt* aus dem vollständig geprüften Produktquellstand `650a2c8408b7e068b84fd8a5d202e21dcaf17330` erstellt – keine Übernahme älterer, ungesicherter Forschungs-Codebasis.

## Unabhängige tatsächliche Prüfung – kein selbst erzeugtes Sustain-Orakel

Authentifiziertes P214-SoundFont-Ausgangsblob `4768c4a0215abf49c7a2bb51ada5ba3494faa1c5`; daraus abgeleitete unverändert originalgesampelte P214-Bank SHA-256 `fd49ab51447262e843d3d547290a12aad2176553f47ec66c30039f3844dcc97c`. Verbindliche, *früher unabhängig mit originalem Creative-Win95-Treiber gemessene* 28 Original-Registerwerte stammen aus [P214 #42737751948](https://github.com/challanger2000/125A-Engineering/actions/runs/42737751948), nicht aus einem Modell im P216-Code. 28 Programme und vier unterschiedliche Instrument-Grundwerte. Sowohl P190-Baseline als auch korrigierter P216-Produktcode wurden als eigenständige tatsächliche native 86Box-EMU8000-Engines gebaut; Testbank geladen, echte MIDI-Stimmen gespielt und Registertraces verglichen.

| Gate | Originalprodukt | Korrigierter P216 |
| --- | ---: | ---: |
| Creative-Original Sustain DCYSUS high-byte | 15/28 | **28/28** |
| Neue Instrumentbasen 0/250/1000 | nicht vollständig passend | **21/21** |
| Base-500-Kontrollen | nicht vollständig passend | **7/7** |
| Native gezielte CTests | 4/4 | **4/4** |
| Unbetroffene Voice-Register zwischen beiden Builds | – | **bitidentisch** |
| 9 mutierte Original-Belege/Quellzuordnungen | – | **9/9 erkannt** |

## Vollständige Windows-VST3-Abnahme (GitHub Actions Windows 2022)

| Prüfung | Ergebnis |
| --- | --- |
| Produkt-VST3 x64 Release kompiliert | **PASS** |
| Gesamte Suite `ctest` | **67/67 PASS** |
| Steinberg-SDK-Selbsttests | **47/47 PASS** |
| Tatsächlicher Steinberg-Modulvalidator | **537/537 PASS** |
| Echter EditorHost GUI-Kurztest | **3 × 57 Interaktionen PASS** |
| Echter EditorHost GUI-Volltest | **99/99 PASS** |
| Unabhängiges 125A Plugin Test Lab (echter Modul-Host, Projektzustand, duale Instanzen, GUI) | **TECHNICAL_PASS** |
| Echtzeit-Callback-Deadline-Überläufe, aktuelle isolierte CI-Matrix | **0/14.400, PASS_LAB_ONLY** |
| Echte DAW und ASIO am Nutzerrechner | **NOT RUN** |
| Originale physische Creative AWE64-Hardware/Klangparität | **NOT RUN** |
| Vollständige unabhängige Release-Abnahme | **NOT RUN / NO-GO** |

Die vorangegangenen P216-Fehlläufe waren **kein** früheres produktives PASS: Ein invalider YAML-Workflow, anschließend der echte SF2-Testfund zur ungültig gewordenen Layer-Provenienz und schließlich ein nicht unterstütztes natives Probe-CLI-Argument wurden jeweils getrennt behoben. Nur das Commit `50dbd6713736b9c60bb33a3a5c737e57b926fd64` trägt den kompletten grünen Nachweis. Vorhandene Prüfanforderungen wurden **nicht abgeschwächt**.

## Belegartefakte, alle aus #42742531063

- Native Original-Creative-P216-Registervergleiche: `P216-Creative-Original-Driver-vs-Real-Product-EMU8000-28-Program-Native-Gate`, Artefakt-ID **13729488158**.
- Vollständige numerische Windows-Evidenz: `P216-Creative-Sustain-Full-Windows-Regression-A`, Artefakt-ID **13729839437**.
- Kompilierter Windows-x64-VST3-Testbuild (nicht verkaufsfertig): `P216-Creative-Sustain-Windows-x64-VST3-TEST-A`, Artefakt-ID **13730536169**.

**Status:** Technisch geprüfte, gezielte Korrektur bereit für den nächsten dokumentierten Hardware-/DAW-Praxistest. **Kein Merge, keine Versand-/Verkaufsfreigabe.** P190s historische RT-FAIL-Messungen werden durch einen einzelnen neuen 0/14.400-Laborlauf nicht rückwirkend annulliert.
