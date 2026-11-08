# P166 — Exakte SoundFont-Presetverwaltung und explizite Wave-ROM-Banken

## Ausgangsbasis und verbindliche Quellen

- Arbeitsbranch: `fix/p166-exact-sf2-rom-isolation`, basierend auf dem erfolgreichen P165-Build `c729fda9cbf2c27723e7a0d5bd39e4e173c6db57`.
- Maßgebliche Regeln: `125A-Engineering/START-HERE.md`, `ENGINEERING-GUARDRAILS.md`, `QA/AUDIT-COMPLETENESS-CONTRACT.md`, `QA/RELEASE-QA.md`, `QA/REALTIME-QA.md`, `QA/AUDIO-FIXTURES.md`, ferner `START-HERE.md` und `AGENTS.md` dieses Projekts.
- Vom Nutzer beschriebene `Synth 512 Bank.sf2`: 77 Presets, Bank 0, echte Programmnummern 0 bis 77 ohne 63. Die verfügbare private Preset-Metadatenliste belegt Reihenfolge/Nummern, enthält **keine Audiosamples**. Die originale .sf2 und Original-Wave-ROM sind NICHT Bestandteil der CI.

## Unabhängig identifizierte Fehlerursachen

1. `PresetCatalog::AppendRomGm` trug ROM-GM-Presets für bisher fehlende Slots direkt in die SF2-Banken 0 bzw. 128 ein; dadurch erschien die falsche 128er Liste.
2. `RomGmBank::LoadBanks` installierte `SYNTHGM.SBK` zuerst ebenfalls als normales Bank-0-/128-Klangmaterial; eine fehlende SF2-Programmnummer konnte deshalb tatsächlich GM-ROM-Audio auslösen.
3. `Synth::NoteOn` suchte bei nicht gefundenem Programm zuerst die GM-Drum-/Bank-0-Alternativen und danach Bank 0/Programm 0 oder eine synthetische Sinusstimme: eine rein visuelle Browserkorrektur hätte die Falschklänge nicht beseitigt.
4. Kanal 10 wurde in `SelectBrowserBank` grundsätzlich von expliziter Bankwahl ausgenommen. Die Anwendung einer spezifischen ROM-Drumbank muss separat möglich sein.

## Korrektur und Nichtänderungen

- `PresetCatalog::AppendRomGm` fügt nur ROM-Metadaten in die eigens reservierten Bänke **16383** (Melodie) und **16382** (Schlagzeug) ein. Es gibt keine automatische Auffüllung der SF2-Bank 0/128 und kein Umnummerieren.
- `RomGmBank::LoadBanks` aktiviert strict mode und lädt eine gültige user-supplied GM-ROM-Deskriptorbank nur als virtuelle ROM-Bänke 16383/16382; die Hardware-Wave-ROM bleibt weiterhin physisch geladen, für Filter/Hüllkurven/ROM-Samples verfügbar. SF2-Samples liegen weiterhin im EMU8000-DRAM.
- `Synth::NoteOn`: Im VST3-strict mode wird ausschließlich die exakt ausgewählte Bank-/Programmnummer bei allen geladenen SoundFonts gesucht. Fehlt diese oder deckt das Preset die Note nicht ab, entsteht **keine neue Stimme**. Weder ROM noch erster SF2-Preset noch Sinustabelle sind Ersatz. Bereits klingende Stimmen werden durch diese Regel nicht automatisch gestoppt.
- Der alte Synth-Modus für historische 86Box-/Spiele-/Treibervergleiche bleibt getrennt verfügbar, so dass die Hardware-Referenzmessungen nicht ungeprüft semantisch geändert werden.
- V11-Format, ParamIDs, 16 Host-Program-Controls, getState/setState und UI-Geometrie bleiben unverändert. Direkte Auswahl, PREV/NEXT und Browser arbeiten weiterhin mit `PresetBrowserModel` und der tatsächlichen phdr-Liste.
- Grenzfall: SF2-Banknummern **16382** und **16383** sind wegen der expliziten ROM-Bänke reserviert; solche Benutzer-SF2 werden mit einer Fehlermeldung abgewiesen, statt heimlich umzunummerieren oder zu überlagern. Die Unfähigkeit, beide Quellen gleichzeitig mit derselben Banknummer abzubilden, ist dokumentiert.
- Die VST3 `IUnitInfo/ProgramList` / 16 MIDI-Programm-Host-Parameter verwenden aus Kompatibilitätsgründen weiterhin den kompletten nummerischen MIDI-Programmraum **0..127**. Das bedeutet **nicht**, dass alle 128 Töne in jeder SF2-Bank existieren; nicht vorhandene Nummern sind audioseitig stumm. Die eigene SF2-Browserliste zeigt sie nicht an.
- Externer MIDI-Programmwechsel behält die originale MIDI-Programmnummer und triggert bei fehlendem Slot keinen Ersatzton. Per Controller gesendete Bank-/Programm-IDs und Projektstate werden nicht normalisiert.

## Automatisierte Verifikation (fail closed)

### A: Unabhängiger Preset- und Audio-Orakeltest

`tests/p166_exact_sf2_rom.cpp`, `125A_p166_exact_sf2_rom`:
- eigens synthetisierte SF2 im Original-77er Nummernbild (Phdr in umgekehrter Reihenfolge), explizites Loch 63; 77 SF2- und 129 isolierte ROM-Metadaten inklusive Schlagzeug;
- weitere SF2 mit mehreren, ungeordneten, nicht aufeinanderfolgenden Programmnummern und separaten MIDI-Bänken;
- Suche, exakte Label, Bankwahl, PREV/NEXT, Direct-Preset, Reservierungs-Kollision und kein stilles Renumbering;
- echte 86Box-Chip- und PCM-Wiedergabe bestehender SF2-Programme, Stille/Nichtallokation für 63/100, echtes ROM-Melodie/ROM-Drum-Audio und MIDI-CC0;
- **negative Gegenprobe** mit absichtlich deaktiviertem strict mode: für Programm 63 wird wieder der unerwünschte Fallback-Ton erzeugt und muss als Negativ-Kontrolle nachweisbar sein;
- V11-Serialisierung inkl. Bank, globalem und channel-spezifischem Programm und exakten Pfaden.

### B: Realer VST3-Processor

`tests/p128_processor_order.cpp` mit Testmodus `p166-exact-presets`, `125A_p166_processor_missing_program`:
- exakt aus realem VST3-`Factory.cpp` extrahierter Processor mit VST3-SDK, echten sample-offset Events und Host-Param-Queues, ROM-gestütztem 86Box-Chip;
- negative PCM-/Stimmen-Proben für fehlendes Programm in mehreren Bänken;
- Host-Automation für Kanal-Programmnummer 63 und unveränderte V11-Save-/Recall-Nummern;
- Gegenprobe mit vorhandenem Programm, plus Projekt-Neuladen mit fehlendem Programm (stumm, nicht durch ROM ersetzt).

### C: End-to-End-Build und unabhängiges Testlabor

`.github/workflows/p166-exact-sf2-rom-windows.yml`:
- Windows-2022, angeheftetes VST3-SDK, mindestens 47 native CTests, Steinberg VST3-Validator, 3 echte Windows-EditorHost-Starts sowie vollständige P165-99-GUI-Aktions-/Pixelregressionen;
- genau eine unabhängig angeheftete Version des `125A-Plugin-Test-Lab` mit **eigenen nativen Hosts**; dessen QUICKCHECK-JSON muss tatsächliche Produkt-DLL-SHA-256 sowie API/PCM-State, Realtime-Stress, Fresh-process Recall, GUI-Lifecycle und Dual-Instance bestätigen;
- der generische Lab-Test für `preset_semantics` bleibt `NOT COVERED`; dafür sind explizit die unabhängigen P166-A/B-Tests verantwortlich. Weder Labor noch SDK-Validator dürfen alleine aus technischen Ergebnissen eine musikalische Produkt-Releasefreigabe erteilen.

## Noch nicht automatisch nachgewiesen (NO-GO)

- Die originale private `Synth 512 Bank.sf2` wurde nicht mit ihren Original-PCM-Waveforms in Windows-CI geöffnet oder abgehört, weil ihre Audiosamplebytes fehlen. Das synthetische 77er-Nummernbild ist ein **gezielter technischer Regressionsnachweis**, keine Behauptung über die originale SoundFont.
- Echte Creative-Wave-ROM-/`SYNTHGM.SBK`-Bitidentität und Hardware-Audiovergleich sind nicht enthalten. Nur synthetische ROM-/SBK-Daten dürfen in öffentlichen QA-Fixtures gespeichert werden.
- Physisches ASIO (Audient usw.) und die Nutzer-DAW-Integration bleiben **NOT RUN**. Ein grüner GitHub-Prozess ist **keine** kommerzielle Releasefreigabe.

**Versionsstatus:** Entwicklung/Validierung. Release bleibt NO-GO bis alle verpflichtenden Tests den *exakten* P166-Commit belegen und nachgelagerte private/physische Abnahmen vorliegen.
