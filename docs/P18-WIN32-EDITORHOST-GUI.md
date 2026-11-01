# P18 – realer Windows-GUI-Hosttest (Steinberg EditorHost)

Der P17-Compilerlauf 15/15 CTest und 47/47 Validator konnte keine Maus-/Tastaturbedienung des VSTGUI-Editors nachweisen.

## Testaufbau

- Windows-2022 GitHub Actions (nur Entwicklungszweig).
- Gepinnter Steinberg SDK 3.8.1, Referenzanwendung **EditorHost** wird als zusätzliches CI-Target gebaut.
- Der Host lädt den vollständigen `.vst3`-Ordner und öffnet `IPlugView` in einem echten Win32-HWND.
- Das Win32-Smoketestskript wartet auf ein tatsächlich sichtbares Hostfenster, prüft die Größe und zeichnet Bitmap-Screenshots auf.
- Test-SF2 mit synthetischen Presetnamen `125A PIANO`, `RETRO LEAD` und `ROOM DRUM KIT`, darunter SF2-Bank 128, wird nur temporär im Runner erzeugt; keine privaten Benutzerdateien/ROMs im Repository.
- Bedienung über tatsächliche Win32-Maus-/Tastatureingaben: BROWSER öffnen/schließen; Creative CQM wählen, PREV/NEXT; EMU8000; Suche `DRUM`; Eintrag mit Bank 128; Editor sauber schließen.
- Veränderungen sichtbarer Bildbereiche werden anhand von Bitmap-Pixeldifferenzen geprüft. Keine Texterkennungsbehauptungen und kein Ersatz von Hostinteraktion durch Quelltextregeln.

## Evidenz und Einschränkungen

- Screenshots und JSON der Bedienprüfungen werden als `125A-P18-EditorHost-Win32-GUI-Evidence` hochgeladen – auch bei CI-Fehlern.
- Fehlender interaktiver Runner-Desktop und Fenster-/Screenshot-Probleme werden als **FAIL** gemeldet, niemals als PASS fingiert.
- Der Windows-VST3-/Steinberg-Validator-Lauf bleibt Pflicht.
- **Das ersetzt keinen Projekt-Recall-/Audio-Test in einem echten Host.** Der EditorHost ist eine Referenzanwendung nur für GUI-Interaktion; finaler Studio-One-Abnahmetest bleibt separat.
- Screenshots sind die Grundlage der folgenden 125A/Sound-Blaster-Retro-Gestaltung; autorisiertes 125A-Masterlogo darf nicht per Font nachgebaut werden.

Status: **NOT RUN – CI-Auswertung folgt.**