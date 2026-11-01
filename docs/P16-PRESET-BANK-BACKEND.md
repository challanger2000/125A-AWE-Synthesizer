# P16 – Preset- und Bankverwaltung (Backend)

Status: Entwicklungsstand, Windows-CI noch nicht ausgewertet. Kein fertiger GUI-Browser.

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
| Originalnamen SF2/IBK + Banken 0,2,128 | 125A_p16_preset_catalog | CI AUSSTEHEND |
| Fehlerhafte, doppelte, abgeschnittene Metadaten | 125A_p16_preset_catalog | CI AUSSTEHEND |
| Echte Audioausgabe Bank 0/5/128 | 125A_sf2_audio_integration | CI AUSSTEHEND |
| CC0-MIDI-Override | 125A_sf2_audio_integration | CI AUSSTEHEND |
| V7, Altformate V1-V6, ungültige Banknummern | 125A_asset_state | CI AUSSTEHEND |
| VST3, Validator | Windows Actions | CI AUSSTEHEND |
| GUI-Suche, Browser, Controller-Host-End-to-End | nächster Schritt | NOT RUN |
| Original-SF2 und Studio One Praxistest | spätere Abschlussprüfung | NOT RUN |

Keine unlizenzierte Creative-ROM und keine privaten SF2 im GitHub-Repository.