# P20 – Klangzuordnung: SF2-Namen ohne geladene Samples

**Status: Korrektur implementiert, Windows-CI noch ausstehend.**

## Beobachtung und überprüfbare Ursache

Der Preset-Browser liest die Namen aus der `phdr`-Tabelle einer SF2.
Die Audio-Engine lädt die vollständige SF2 dagegen erst bei VST3-Aktivierung.
Vor P20 wurden mögliche Fehler (fehlender Pfad, defekte Datei, zu große
Sampledaten bzw. 86Box-EMU8000-RAM-Grenze) in `assetError_` gespeichert,
aber dem Benutzer nicht angezeigt. War keine Bank geladen, erzeugte
`Synth::NoteOn()` einen **synthetischen Ersatz-Sinuston** und gab ihn
unter dem tatsächlich nur aus Metadaten gelesenen Preset-Namen aus.
Dadurch konnten mehrere unterschiedliche Programmnamen nahezu gleich klingen.

Die Nutzerbeobachtung war ein tiefer, orgelartiger Klang bei einem
`TX81Z Lately Bass` genannten SF2-Preset. Eine Audiodatei enthielt
einen nahezu reinen 220-Hz-Ton. Das ist **vereinbar** mit dem
Fallback-Sinus, beweist aber ohne die konkrete SF2 und einen
Prozessor-Ladestatus noch nicht, dass die SoundFont-Ladung im
Nutzerprojekt tatsächlich gescheitert ist.

**Keine Diagnose per bloßem Programmnamen:** Ein SF2-Preset mit TX81Z
im Namen ist ein Sampleprogramm im EMU8000, keine 4-Operator-FM-Emulation
des Yamaha TX81Z.

## P20 Verhalten

- Bei explizit konfigurierter SF2 und erfolgreicher `LoadBank()`: EMU8000
  spielt die echte geladene Bank.
- Bei explizit konfigurierter SF2 und `LoadBank()`-Fehler: **keine
  irreführenden Ersatznoten mehr**, sondern Stille in diesem EMU8000-Modus.
- Fehlergrund wird in der VST3-`setActive`-Phase (nicht im Audiothread)
  als Textnachricht an den Controller geschickt und in der GUI-Fußzeile
  angezeigt. Die Fußzeile bleibt beim Schließen des Browsers sichtbar.
- Ohne konfigurierte SF2 bleibt der bisherige Demo-Fallback bestehen,
  aber die GUI kennzeichnet die fehlende SoundFont ausdrücklich.
- Die Yamaha-OPL3- und Creative-CQM-Engine, gespeicherte Projekte,
  Bank-/Programm-IDs sowie SF2-Daten selbst bleiben unverändert.
- Die zuvor erwogene Änderung der SF2-Hüllkurven ist **nicht Teil**
  dieser Korrektur und wurde nicht in den Entwicklungsbranch übernommen.

## Verifikation / Grenzen

- `125A_sf2_audio_integration`: ausdrücklich angeforderte, fehlende
  SF2 führt unter der neuen Policy nicht zu Ersatzklang; erfolgreiches
  Laden und Demo-Betrieb werden nicht blockiert.
- Statischer VSTGUI-Vertrag überprüft Prozessormeldung, Fehlertext,
  GUI-Status und Verhinderung der irreführenden Ersatznote.
- **Vorläufig NOT RUN**: Windows-VST3-Build, 47 Validator-Tests,
  Steinberg-EditorHost, Studio-One-Test mit der betroffenen echten
  SoundFont und Vergleich mit einem Original-/Referenzklang.
- Ein kompletter SoundFont, der die 28-MiB-Hardwaregrenze überschreitet,
  wird **nicht** durch Umbenennung einer Preset-Nummer kompatibel.
  Falls das tatsächliche Dateiformat diesen Fall auslöst, muss die
  Speichernutzung gesondert geprüft werden. Die Dateibezeichnung
  allein beweist keine Dateigröße.

**Keine finale Klanggleichheit und keine Studio-One-Reproduzierbarkeit
behaupten, bevor die tatsächlich verwendete SF2 vorliegt.**
