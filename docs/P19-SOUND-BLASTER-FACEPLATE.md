# P19 — Sound-Blaster-inspirierte 125A-Hardware-Faceplate

Entwicklungsstand vom 1. November 2026. **Nicht FINAL.**

## Ziele und vorhandene Funktion

- P17/P18 bleibt unverändert benutzbar: EMU8000, Yamaha OPL3, Creative CQM, SF2-/IBK-Browser, Suchfeld, Bankfilter, PREV/NEXT und VST3-Parameter-IDs 1000/1001/1002.
- Dunkles, modernes Metallgehäuse mit klar getrennten Hardware-, Instrumenten- und Browserbereichen; keine nostalgischen, kontrastarmen 1990er-Windows-Buttons oder vorgetäuschten Rack-Schrauben.
- **Originales 125A-Masterlogo**, keine Schriftreplik: Quellasset `challanger2000/125A-Branding/125A_Logo_Master_FINAL.svg`, unveränderter Git-Blob `bd398ffa3b728b1a847bb519fad8168222bccb48`.
- VSTGUI zeichnet die unveränderten 30 SVG-Pfade direkt in einem skalierbaren CGraphicsPath. Das Original verwendet Even-Odd-Fill für Buchstabenlöcher; der Renderer bewahrt ihn.
- Das SVG liegt im VST3-Resources-Verzeichnis, keine externen Benutzerdateien. Wenn es fehlt, erscheint lieber kein Logo als eine falsche Rekonstruktion.

## Automatische Prüfungen

- `125A_p19_master_logo`: 30 Pfade, 29 Silber-/ein Rotpfad, >2750 Zeichenbefehle, originale Mehrfachkonturen.
- `tools/verify_logo_resource.py`: exakte Blob-ID in Source und im fertigen Windows-VST3-Bundle.
- Der echte Win32-Steinberg-EditorHost-Test prüft anhand des Screenshots, dass die rote Logo-Kontur im geöffneten Plugin gezeichnet ist, und führt die P18-Browserbedienung erneut aus.
- CTests, Steinberg-Validator und beide FM-Banken bleiben Pflicht; kein Eingriff in Audio-Threads, Synthese-Engines, Projektformat oder die Programmnamen.

## Noch nicht abschließend freigegeben

- Screenshots des realen Windows-EditorHosts visuell auf Überlappungen, abgeschnittene Elemente, Skalierung, Kontrast und Lesbarkeit prüfen.
- Das endgültige Design/Branding mit dem Nutzer abstimmen. Referenz ist ein **moderner Sound-Blaster-Hardware-Look** und die funktionale Bedienung – nicht ein ungeprüftes Verkaufsdesign.
- Studio One 8: abschließende Host-/Projekt-Recall-Abnahme nach allen GUI-Korrekturen. Kein Test nach jeder kleinen Änderung.

**Status: CI-Auswertung ausstehend.**
