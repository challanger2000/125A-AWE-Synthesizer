# P16 – Preset- und Bankverwaltung (Backend)

Status: P16-Backend Windows-CI BESTANDEN; GUI-Browser noch NICHT implementiert.

## Backend

- `PresetCatalog.h` liest SF2/SBK-Presetnamen aus RIFF/pdta/phdr ohne SoundFont-Samples zu laden.
- Banknummer, Programmnummer, Drum-Bank 128 und echte Namen werden als Einträge erfasst.
- Historische FM-Namen werden direkt aus der jeweiligen IBK-Bank eingelesen; Yamaha OPL3 und Creative CQM teilen sich die Metadaten.
- Der VST3-Controller liest die Metadaten bei Initialisierung und beim Projekt-Recall, niemals im Audio-Callback.
- Die Entwickler-GUI mit dem 128-Programme-Dropdown bleibt vorerst unverändert; Suchfeld und Browser sind der nächste GUI-Schritt.

## Parameter und Projektformate

- Program: unverändert ID 1000, 0 bis 127.
- Hardware: unverändert ID 1001, EMU8000, OPL3 oder CQM.
- Neu: SF2 Bank, ID 1002, 0 bis 16383, Default 0.
- AssetState V7 hängt die Banknummer an das bestehende V6-Format an.
- V1 bis V6 werden mit Bank 0 wiederhergestellt, alte Parameter-IDs bleiben unverändert.
- Im Audio-Backend lenkt die Bankauswahl den SoundFont-Presetzugriff wirklich um.
- MIDI CC0 kann die Browser-Vorauswahl auf einem einzelnen MIDI-Kanal überschreiben.
- MIDI-Kanal 10 bleibt gemäß GM auf Bank 128; Bank 128 kann außerdem auf einem melodischen Kanal vorgehört werden.

## Test-Gates

| Vertrag | Nachweis | Status |
| --- | --- | --- |
| Originalnamen SF2/IBK + Banken 0,2,128 | 125A_p16_preset_catalog | PASS – Windows 2026-11-01 |
| Fehlerhafte, doppelte, abgeschnittene Metadaten | 125A_p16_preset_catalog | PASS – Windows 2026-11-01 |
| Echte Audioausgabe Bank 0/5/128 | 125A_sf2_audio_integration | PASS – Windows 2026-11-01 |
| CC0-MIDI-Override | 125A_sf2_audio_integration | PASS – Windows 2026-11-01 |
| V7, Altformate V1-V6, ungültige Banknummern | 125A_asset_state | PASS – Windows 2026-11-01 |
| VST3, Validator | Windows Actions | PASS – Windows 2026-11-01 |
| GUI-Suche, Browser, Controller-Host-End-to-End | nächster Schritt | NOT RUN |
| Original-SF2 und Studio One Praxistest | spätere Abschlussprüfung | NOT RUN |

Keine unlizenzierte Creative-ROM und keine privaten SF2 im GitHub-Repository.
## Verifizierter Prüfstand

- Geprüfter Quellcode: `a13133ed8509dfce02139d2a6d1c69e9cf426113` (P16 + Fix PR #10).
- Windows VST3 Build und vollständiges CTest: [Actions #41266996258](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41266996258) **SUCCESS, 15/15**.
- Steinberg-Validator: **47/47 PASS** im selben Lauf.
- Native Engine-Prüfung: [Actions #41266996267](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/41266996267) **SUCCESS, 13/13**.
- VST3 Paket einschließlich MAUIFM.IBK und DRUM.IBK durch SHA-Prüfung bestätigt.
- **NICHT geprüft:** fertiger Preset-Browser, GUI-Suche und Bankliste, VST3 Controller/Host-End-to-End mit Benutzerbedienung, DAW-Projekt-Recall in Studio One und echte Nutzer-SF2s. Für P17 sind diese Punkte explizite Testaufgaben.
- Kein Gumroad-/FINAL-Release und kein erneuter Studio-One-Test angefordert.
