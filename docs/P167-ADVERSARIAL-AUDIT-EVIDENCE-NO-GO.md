# P167 — Adversarialer Audit von 125A-AWE-Synthesizer P166 (Audit ist **NICHT vollständig**)

**Datum:** 2026-11-08  
**Ziel-Repository:** `challanger2000/125A-AWE-Synthesizer`  
**Unveränderlich gepinnter geprüfter Produktstand:** `fix/p166-exact-sf2-rom-isolation`, SHA `6395d4cf1d027ae2f01b73ed2a6e658121a469c9`  
**Ausgangsbasis:** erfolgreiches P165-GUI, SHA `c729fda9cbf2c27723e7a0d5bd39e4e173c6db57`  
**Audit-only branch:** `audit/p167-p166-adversarial-test-gate`, reproduzierender SHA `9ffbfb9b69e4bbb15cce5ac823137e7278344f99`. **Nur Tests und CI ergänzt, kein Produktionscode verändert.**  
**Normen:** `125A-Engineering/START-HERE.md`, `README.md`, `ENGINEERING-GUARDRAILS.md`, `QA/AUDIT-COMPLETENESS-CONTRACT.md`, `QA/RELEASE-QA.md`, `QA/REALTIME-QA.md`, `QA/AUDIO-FIXTURES.md`, `STANDARDS/PROFESSIONAL-PLUGIN-BEHAVIOR.md`, plus `START-HERE.md` und `AGENTS.md` des AWE-Repositories.

## Endurteil (ohne Relativierung)

- **PRODUKTKORREKTHEIT: FAIL.** Ein neuer, reproduzierbarer Fehler in der Auswahl von SF2-Bank 0 auf MIDI-Kanal 10 erzeugt den Klang der **falschen, tatsächlich vorhandenen Bank 128**. Sowohl der reale native Synth/EMU8000-PCM-Pfad als auch der exakt aus `Factory.cpp` extrahierte VST3-Processor sind betroffen.
- **P166-PRESET-KORREKTUR ALS GANZES: KEIN PASS.** Die 77-zu-128-Auffüllung wurde in gezielten Tests behoben, aber die in der Anforderung verlangte durchgehend exakte MIDI-Bankzuordnung ist widerlegt.
- **RELEASE: NO-GO.** Den P166-Test-VST3 nicht als RELEASE/FINAL/Gumroad-Paket einstufen.
- **FULL AUDIT: NICHT NACHGEWIESEN.** Die systematische Bestandsaufnahme und gezielten unabhängigen Fehlergegenproben reichen nicht aus, um alle produktiven Funktionen, die gesamten Testimplementierungen, alle Fremdabhängigkeiten und Echtzeit-/DAW-/Hardware-Gates als vollständig geprüft zu bezeichnen. Die unten aufgeführten Lücken gelten **NOT RUN bzw. NOT REVIEWED**, niemals PASS.

## Vollständigkeitskontrolle und Scope

Die GitHub-Git-Tree-API lieferte zum **exakten P166-SHA** einen **nicht abgeschnittenen** rekursiven Tree mit **397 Dateiobjekten**. Eingeteilt: `src/engine` **12** Textdateien, `src/vst3` **28** Textdateien + **12** Assets, `src/opl3` **5**, `tests` **64**, `tools` **76**, `.github/workflows` **55**, `third_party` **7**, `upstream` **61**, sonstige **77**. Ein vollständiger Dateibaum ist **keine** vollständige Code- oder Testdurchsicht.

**Tatsächlich nachverfolgt:** Alle 11 P166 gegenüber P165 geänderten Dateien und deren bank-/presetbezogenen Änderungen anhand des GitHub-Commitvergleichs; Controller/Processor-Einstieg, `process`, `getState`, `setState`, MIDI-Event-/CC-Scheduling, Bank-Reihenfolge, SF2-Katalog und Browser-Auswahl, `Synth::NoteOn`/Bank- und Voice-Pfad, `RomGmBank::LoadBanks`; maßgebliche Teststellen in `p166_exact_sf2_rom.cpp`, `p128_processor_order.cpp`, `p122_vst3_bank_host.cpp`, `p117_direct_preset_selection.cpp`, `p120_vst3_program_host.cpp`, `sf2_audio_integration.cpp` und der realen Windows-P165-EditorHost-Acceptance. Kleine produktive Header (AssetState, AssetConfig, BankOrder, BrowserBankCommand, MidiLiveState, MidiControlMapping, MidiProgramRouting, MidiQueueOrdering, RealtimeEngineExchange, RealtimeStateVersion, MasterOutput, PitchZeroFlush, HostNotificationRetry, WinUiDispatch) wurden direkt gelesen. SF2-Parser- und Hüllkurvenpfade wurden stichprobenartig kritisch nachverfolgt.

**NICHT als vollständig gelesen/verifiziert geltend machen:** alle Verzweigungen der großen `src/engine/{SoundFont.cpp,Synth.cpp,Emu8000.cpp,snd_emu8k.c,Emu8000Box.cpp}`; vollständige Effekt-/Filter-/DSP-Register-Treue, vollständige Originaltreiber-/ROM-Funktionen, die restlichen unabhängigen Testimplementierungen, historische Tools/Win95-Bridge, 55 historische Workflows, gesamter vendorter Upstream, jede OPL3/CQM-Altkomponente. Insbesondere sind die 64 Testdateien nicht allesamt adversarial einzeln auf ihre Falsifikationsfähigkeit geprüft. **Deshalb fehlt der im Audit-Completeness-Contract erforderliche vollständige Source/Test-Review-Nachweis.**

## F01 — HOCH, nachgewiesener falscher Bankklang

**Ort:** `src/engine/Synth.cpp`, `Synth::BankNumberFor`, ca. Zeilen 1022–1034 und `Synth::ControlChange`, ca. Zeile 1736. `Synth::NoteOn` verwendet diese Banknummer direkt zur Auswahl der realen SoundFont-Regionen.

**Fehlerursache:**
```cpp
if (m_strictPresetSelection) {
    if (selection.browserBankActive) return selection.browserBank;
    if (channel == 9 && selection.bankMsb == 0) return kDrumBank;
    return selection.bankMsb;
}
```
`ControlChange(9,0,0)` setzt `bankMsb=0` und `browserBankActive=false`. Die vorstehende Bedingung deutet eine **ausdrücklich empfangene Null** fälschlich als **unberührte GM-Schlagzeug-Vorgabe** und wählt **Bank 128**. Zwei SF2-Presets sind an den verschiedenen Bankplätzen vorhanden und erzeugen unterschiedliche Töne. Das ist ein **falscher Klang**, nicht nur fehlende Browser-Anzeige. Der Quellcode-Kommentar, ein echtes CC0 wähle danach die tatsächliche Bank, ist damit widerlegt.

**Gegenprobe 1 — reeller nativer 86Box-Synth:**
- Audit-only-Erweiterung des bestehenden synthetischen `tests/p166_exact_sf2_rom.cpp`: copyrightfrei generierte SF2 mit 2 vollständig vorhandenen, unterschiedlich klingenden Sounds an `bank0:program0` und `bank128:program0`. Für beide wird echtes Stereo-PCM über den EMU8000-86Box-Kern gerendert und als 64-Bit-Fingerprint verglichen.
- **PASS:** beide Referenzklänge spielen, haben unterschiedliche Fingerprints. Alle 17 bisherigen P166-Checks bleiben PASS.
- **FAIL:** browser bank128 -> **MIDI Kanal10 CC0=0** -> program0 -> Noten; die tatsächliche Ausgabe entspricht weiter bank128 statt bank0.
- GitHub [P167 Windows #42432191611](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42432191611), Test-Ergebnisdatei `adversarial-stdout.txt`, Audit-SHA `3c0fcf4f62d38c4ef74f20fa366c572e4c8e85f9`. Der Workflow hat nur deshalb **SUCCESS**, weil er explizit genau **einen nachgewiesenen Fehler**, einen bestandenen unabhängigen Klang-Kontrollcheck und einen nativen Exitcode 1 verlangt. Dies ist ein **erfolgreich fehlgeschlagener Produkttest**.

**Gegenprobe 2 — originaler VST3-Processor über echte Host-Queue:**
- `tests/p128_processor_order.cpp` bekam audit-only den Test `p167-channel10-bank-zero`. Der exakt gleiche Produktions-Processor wird aus unverändertem `src/vst3/Factory.cpp` per `p128_extract_processor.py` erzeugt, mit Steinberg-VST3-SDK und echter `ParameterChanges`-/`EventList`-Queue betrieben. Sample-accurate `process()` + 86Box erstellt Audio-PCM.
- **PASS:** bank0/program0 versus bank128/program0 auf Kanal 10 sind unterschiedliche, hörbar nachweisbare PCM-Referenzen.
- **FAIL:** ParamID des Kanal-10-CC0 mit Wert **0** übersetzt in den **falschen** Drum-PCM-Pfad. Original-Hostausgabe: `PASS ... distinct SF2 bank0 versus bank128 PCM`, `FAIL ... explicit CC0=0 selects bank0 PCM`, `RESULT checks=2 failed=1`.
- GitHub [P167 tatsächlicher Processor #42432757481](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42432757481); Artifact `P167-Actual-VST3-Processor-Ch10-CC0-PCM-Falsification`, Audit-SHA `9ffbfb9b69e4bbb15cce5ac823137e7278344f99`. Wieder ist **SUCCESS** der CI-Überwachung ausschließlich das erwartete, reproduzierbare **FAIL des Produkts**.

**Warum P166 Grün anzeigte:** Die eigene P166-CC0-Probe verwendete **MIDI-Kanal 1** (zero-based 0), nicht Kanal 10 (zero-based 9). Tests für fehlendes Programm 63 entdeckten keine Verwechslung von zwei tatsächlich vorhandenen, unterschiedlich klingenden Programmen. Die allgemeinen 47 CTests, der Validator und die 99 GUI-Checks bilden diese spezielle MIDI-CC-Null-Zuordnung nicht ab. Der generische Test-Lab-Status `TECHNICAL_PASS` sagt ausdrücklich **`preset_semantics=NOT COVERED`**.

**Maßnahme für Entwickler:** Die explizite Empfangshistorie von CC0/CC32 darf nicht anhand `bankMsb==0` erraten werden: Zustandsbit `CC0 explizit empfangen` (einschließlich Zeit-/Vorrangslogik zu Browser- und Recall-Bank) nötig. Unberührte GM-Kanal-10-Vorgabe bewusst beibehalten, **ausdrückliche CC0=0** aber als Bank 0 verarbeiten. Testmatrix alle 16 Kanäle, bank0/bank5/drum128/virtuelle ROM-Banken, CC0 0/mehrfach 0, CC32, gleichzeitiges Host-Programm, Engine-Tausch, Recall und folgendes Audioblock. Exakte PCM-Identität statt nur `audible=true`. **Audit hat ausschließlich den Fehler reproduziert, nicht Produktionscode verändert.**

**Verfolgung:** [Produkt-Issue #80](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/80), Engineering-Präventionsentwurf [#44](https://github.com/challanger2000/125A-Engineering/pull/44).

## F02 — MITTEL, durch Quellcode nachweisbarer Anzeige-Widerspruch; reale DAW-Reproduktion NOT RUN

**Ort:** `src/vst3/PresetBrowserView.cpp` `SyncActiveMenuSelection`, ca. Zeilen 774–784:
```cpp
const auto current=std::find(activePrograms_.begin(),activePrograms_.end(),program_);
programMenu_->setValue(current==activePrograms_.end()?0.f:
    static_cast<float>(current-activePrograms_.begin()));
```
Bei Host-Programm 63 der originalen 77er-Bank ist `program_=63`, `activePrograms_` enthält **63 nicht**. Der Code setzt das aktive Programmmenü trotzdem auf **Index 0**. Gleichzeitig zeigt `programLabel_` über `PresetBrowserModel::CurrentLabel` „Nicht in der Bank vorhanden“ und der Strict-Synth bleibt stumm. Dieses Auseinanderfallen von Menüanzeige und tatsächlichem Programm ist **am Quellcode objektiv ablesbar**; ein gezielter EditorHost/DAW-Screenshot der echten Host-Automation auf Programm 63 ist **NOT RUN**. Fehlerstatus **STATIC CONFIRMED / VISUAL NOT VERIFIED**, nicht vollständiges GUI-FAIL aus Screenshot.

**Maßnahme:** „Nicht vorhanden (63)“ als eigene nicht-klingende Anzeige oder expliziten nicht selektierten Menüstatus darstellen, nie Index0 als vermeintlich aktuelles Preset. Test mit externem Host-Programmwechsel während offenem/geschlossenem Browser, MIDI-Program63, Autosync und Recall.

## Vertragskonflikt und weitere nicht unabhängig geklärte Risiken

**F03 — VST3 Host-Program-Listen gegen „nur vorhandene Presets“ (VERTRAGSKLÄRUNG OFFEN):** `src/vst3/Factory.cpp` `Controller::initialize`, ca. Zeilen 1898–1942, veröffentlicht fest **128** Programmlistenplätze pro MIDI-Kanal über `IUnitInfo` und ein globales 128-Eintrag-`StringListParameter`. Das P120-Hosttestprogramm erzwingt explizit `programCount==128` und prüft gerade **nicht** die 77 tatsächlich vorhandenen SoundFont-Programme. Das kann eine beabsichtigte Kompatibilitätsentscheidung für den numerischen MIDI-Adressraum 0..127 sein; es ist kein Beweis für zusätzliche ROM-Klänge und nicht automatisch ein funktionaler Fehler. **OFFEN** bleibt, ob der Ziel-DAW-Host diese 128 Nummern als 128 „vorhandene Instrumente“ anzeigt, wodurch die Benutzeranforderung erneut verletzt würde. **Ziel-DAW-Abnahme NOT RUN**.

**R04 — getState unter ununterbrochener Automation (RISIKO, NOT RUN):** `Factory.cpp` `getState` (ca. Zeilen 555–605) versucht 4096 optimistische Snapshots und danach einen control-only `for(;;)`-Doppelread der Host-Intent-Atomics, bis sie gleich sind. Die ausschließende `RealtimeStateVersion::Writer`-Sperre verhindert RT-Änderungen der Persistenzfelder, **aber nicht zwingend die vor dem Writer-Gate veröffentlichten Absichten**. Bei dauerhaft wechselnden Automation-Intents ist aus dem Quellcode keine feste obere Wartezeit des control-side Fallbacks ersichtlich. Das ist ein **nicht reproduzierter Liveness-/Host-Save-Risikopfad**; die bisherigen 500/500-Save-Tests schließen genau diesen adversarialen Endlos-Producer nicht aus. Es fehlen ein harter Timeout-Falsifikationstest, Resultat und unabhängig belegte Realtime-Deadline-Messung.

**R05 — MIDI CC32/14-Bit-Banknummerierung (OFFEN/NOT RUN):** `Synth::ControlChange` speichert `bankLsb`, `BankNumberFor` wertet nur `bankMsb` oder Browser-Bank aus. Ob die echte Creative-EMU8000-Zuordnung einer MIDI-14-Bit-Bankauswahl dies verlangt, ist ohne verbindliches Protokoll-/Hardware-Orakel ungeklärt. Nicht als bewiesener Fehler einstufen; unabhängigen Bank-Select-Vertrag spezifizieren und testen.

**R06 — ausgelagerte Abhängigkeiten, 28-MiB-RAM, DSP/Filter/Hüllkurven, GUI-Zoom, Offline/ASIO:** Die vollständigen Eingabe-/Speicher-/Samplegrenzen jeder Engine-Funktion, alle DSP-Register-/Chorus-/Reverb-Modi, jede Legacy-OPL3-Abhängigkeit sowie exotische Hostbusszenarien sind hier **nicht** separat vollständig adversarial auditiert. Keines dieser Themen erhält aus allgemeinen CI-Grünmeldungen einen pauschalen PASS.

## Beweis-Matrix — Ansprüche und Grenzen

| Anforderung / Testfamilie | P166 bereits ausgeführt | P167 unabhängig geprüft | Wertung |
| --- | --- | --- | --- |
| Pinned Git-SHA und unveränderter Produktionscode | P166 `6395d4c` | P167-Diff enthält nur Test/YAML | PASS Provenienz |
| Synth-512 Original-`phdr`, 77 Presets, echte Nummern, kein 63 | synthetische 77er SF2 | private Originaldatei unabhängig binär gelesen: **77**, Bank0, 0..77 ohne 63, unsortierte `phdr` | PASS **Metadaten**, nicht originale Windows-PCM |
| ROM als eigene Presetbank 16383/16382 | P166 `p166_exact_sf2_rom` PASS | synthetische 86Box-PCM-Gegenprobe passabel | PASS nur **synthetischer** Pfad |
| Nicht vorhandene Programmnummern erzeugen keinen ROM-Ersatzton | P166 Synth und Processor PASS | negative Strict-Aus-Probe prüft tatsächlichen Ersatzton | PASS nur geprüfte synthetische Fälle |
| PREV/NEXT und Browser-Tabelle | P166 Unit + P165 GUI99 PASS | nicht alle Host-MIDI-/automationsabhängigen Anzeigezustände getestet; F02 | PARTIAL/INCONCLUSIVE |
| Bank- und Programmnummern bei **allen** MIDI-Kanälen | nur Teilmatrix P166 | **F01 doppelt über echten PCM und Processor falsifiziert** | **FAIL** |
| VST3 Host-IUnitInfo ausschließlich echte 77er Presets | 128 numerische Programmslots als Testvertrag PASS | Hostanzeige in Ziel-DAW NOT RUN | OFFEN |
| Save/Load, per-channel Host-Program, Recall, konkurrierende Writer | 47/47 CTests inkl. P122/P128 PASS | kein vollständiger kombinierter 16-Kanal-CC0+CC32+Recall+Alterungsstress | PARTIAL |
| Steinberg VST3 Validator | 537/537 PASS am P166 exakt | testet nicht 16-Kanal-PCM-Semantik | PASS Validator allein |
| Echte native EditorHost-Bedienung | 3 Smokes + 99 Interaktionen PASS | kein Programm-63-Hostdropdown-Gegenbeweis | PARTIAL |
| 125A Plugin-Testlabor | `TECHNICAL_PASS`, Produkt-SHA geprüft, `release_approved=false` | `preset_semantics` nicht vom generischen Lab abgedeckt | PASS **generische Labtechnik**, nicht Produkt-Presets |
| Eigene reale `awe32.raw` + eigene `SYNTHGM.SBK` + private SF2 als echtes VST3-Audio | nicht im öffentlichen CI | Originaldateien vorhanden/Metadaten geprüft, aber **kein** originaler 86Box-Windows-VST3-PCM-A/B-Lauf | NOT RUN |
| Physischer Audioausgang/ASIO, Ziel-DAW, Preset-Hörvergleich | kein bestätigtes P166-DAW/ASIO-Audit | NOT RUN | NOT RUN |
| Vollständiges Source-/Test-/Dependency-Inventar **und** vollständiger semantischer Review aller Einheiten | 397 Dateien inventorisiert | zentrale große DSP-/Upstream-/Testgebiete nicht lückenlos geprüft | **NOT COMPLETE** |
| Echter zweiter unabhängiger Auditor mit eigenem Zugang/Orakel | nicht vorhanden | Selbstaudit mit zwei gegensätzlichen ausführbaren Gegenproben, kein separater Reviewer | NOT RUN |

## Originale private SoundFont-/ROM-Daten (lokal, nicht zu GitHub hochgeladen)

Die bei der Audit-Analyse verfügbaren, ausdrücklich **nicht veröffentlichten** Originaldateien wurden separat auf Identität und Metadaten geprüft:
- `Synth 512 Bank.sf2`: **555754 Bytes**, SHA-256 `d5b99ec38fddf59f53f66b90921e170d207bf3bbd73960f6e4175c39ef68349b`, **77** SF2-Presets in Bank0, fehlende Programmnummer **63**, **521842** PCM-Samplebytes;
- `Callanish.SF2`: **8251362 Bytes**, **23** Presets, `phdr` unsortiert;
- `FM Dreams Sampler.sf2`: **1394908 Bytes**, **35** Presets, `phdr` unsortiert;
- `SYNTHGM.SBK`: **34832 Bytes**, ROM-GM-Deskriptor, separat; `awe32.raw`: **1048576 Bytes** (Wave-ROM).
Diese Metadatenprüfungen sind unabhängig von der Produkt-CI. Ein SoundFont-Dateihash, eine Dateigrößenprüfung oder eine Audioausgabe durch einen **anderen** SoundFont-Player beweist **nicht** die EMU8000-Hardwaretreue bzw. den tatsächlichen Windows-VST3-PCM-Pfad mit diesem Original.

## Konkrete Abnahmereihenfolge und unveränderte Produktgrenzen

1. **F01 beheben und zuerst ROT/GRÜN-Wirkung beweisen:** produktive Implementierung mit explizitem Bank-„touched“-Zustand; beide P167-Synth- und Processor-Proben müssen von nachweislich reproduziertem FAIL zu PASS wechseln; eine Test-only-Reversion der Fehlerbedingung muss sie erneut ROT machen.
2. Fehlende 63 und vorhandene Programmnummer 64 in **echter GUI** unter Host-Programm-Änderung testen; sichtbaren ersten Menüeintrag nicht fälschlich als angewählt markieren; Host-IUnitInfo-Vertrag und Anzeige im Zielhost ausdrücklich klären.
3. Channel0..15-Gegenproben mit realem Processor: CC0=0, >0, CC32, Browserbank, unterschiedliche Presets/PCM, Bank-/Programmwechsel gleiche Sampleposition, Eventordnung, V11 Recall und kontrollierter Engine-Swap; 16-Kanal-Matrix mit selbstverschiedenen Quellklängen.
4. Auditinventar bis zur letzten produktiv relevanten Datei/Testfunktion vervollständigen; DSP, SF2-Parser, 86Box-PCM, 28MiB-Grenzen, Threads, Loop-Hüllkurven, MIDI/Host-Fehlerverhalten und alle Pflichtstandards systematisch gegen unabhängige Orakel.
5. 47+ komplette Windows CTests, Validator, realer EditorHost, streng getrennte generische Test-Lab-Berichte, Test-Lab-Produktschnittstelle und Deadline-/ASan-/UBSan-/Concurrent-Save-Stress **auf dem exakt neuen Fix-SHA** wiederholen. Eine grüne Regression ohne überprüfte Fehlererkennung ist kein FULL AUDIT.
6. Private Original-SF2 + echte Wave-ROM + SYNTHGM im echten Windows-VST3 ansteuern, Audio/Bankwechsel aufnehmen, mit Kontrollklang vergleichen. Danach Benutzer-DAW und physisches ASIO separat abnehmen; bis dahin NOT RUN.

**Berechtigungs- und Liefergrenze:** P166-Produktbranch, `main`, Creative-ROM und Gumroad-Paket bleiben **unangetastet**. Audit-only-Nachweise sind unter `audit/p167-p166-adversarial-test-gate` und Produkt-Issue [#80](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/80) dokumentiert. Die verbindliche Engineering-Guardrail ist als separater **Draft** PR [125A-Engineering #44](https://github.com/challanger2000/125A-Engineering/pull/44) vorbereitet, nicht ungeprüft auf `main` gepusht.

**FAZIT:** **Bestätigtes Release-blockierendes FAIL** mit zwei echten PCM-Gegenproben. Der im Auftrag geforderte **FULL AUDIT** ist aufgrund konkret ausgewiesener nicht geprüfter Quellteile, Testfunktionen, Echtzeit-/DAW-/Originalhardware-Gates **nicht vollständig**. Ein FULL-AUDIT-PASS ist ausdrücklich **nicht** vergeben.
