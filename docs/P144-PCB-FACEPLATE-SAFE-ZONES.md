# P144 — PCB-Soundkarten-Frontplatte: Komponentenfreie Zonen

**Arbeitsgrundlage:** P143 `96a457b442a28af0a8ac6e95048749eb70508a93`, erfolgreich geprüfte native Windows-x64-VSTGUI; 1000 × 640 **logische** Pixel. **Dieses Dokument verändert keinen GUI-Code, keinen DSP und keinen VST3-Parameter.** Artwork darf erst nach kontrolliertem Einbau und erneutem EditorHost-Test als integriert gelten.

## Gestaltungsprinzip

**Erst physische Montageflächen, dann Schaltkarte.** Kein gezeichnetes IC-, Kondensator-, Widerstands- oder ISA-Kontakt-Bauteil unter Reglern, Drehkränzen, Schaltern, Menüs, editierbarem Text, Statusanzeigen oder Beschriftungen. Die Sperrzonen schließen die sichtbaren Labels und einen Sicherheitsabstand ein. Leiterbahnen dürfen in unbenutzten PCB-Zonen laufen, nicht über lesbare Schrift oder über die Standfläche eines Reglers; optisch hinter einer bewusst geschlossenen Montageblende verlegte Traces sind davon ausgenommen.

Die Soundkarte bekommt **zwei verschiedene Artwork-Schichten**:
1. **Gemeinsame Frontplatte:** Grundmaterial, Farbe, Panelrahmen, sehr feine Traces, die alle MAIN/EDIT/BROWSER-Zonen respektieren. Hier gelten die Sperrflächen **aller drei Seiten vereinigt**.
2. **Seitenspezifische Artwork-Schicht:** Nur auf der jeweils angezeigten MAIN-/EDIT-/BROWSER-Seite, jeweils **hinter** deren nativen VSTGUI-Kontrollen. Dadurch kann auf MAIN links ein großer EMU8000-Chip sitzen, während dort in EDIT die AMP/Filter-Bedienung funktioniert. Niemals die MAIN-Chip-Grafik auf EDIT durchscheinen lassen.

Die Layer sind reine Zeichnung: `setMouseEnabled(false)`, keine Parameteränderung, kein hit-test-Overlay und keine Veränderung an `valueChanged`, Automation, Preset-Recall, State V11 oder Ladeaktionen. Das EMU8000-IC darf eine **dekorative Darstellung** sein, aber keine falsche Behauptung einer exakten Pinbelegung.

## Immer gesperrt: alle Ansichten

| Bereich | Sperrrechteck (x1,y1)–(x2,y2) | Grund |
| --- | --- | --- |
| Kopfzeile | (12,8)–(988,55) | 125A-Masterlogo, Name, EMU8000 und Stimmenanzeige |
| LCD + Dateifunktionen | (12,64)–(988,203) | Preset-/ROM-/SF2-/RAM-Status, ROM/SF2-Ladetasten |
| Bank/Preset | (12,210)–(988,261) | Bankwahl, PREV/NEXT, Presetmenü |
| Navigation | (12,267)–(988,305) | MAIN, EDIT, BROWSER, feste Navigationstexte |
| Statuszeile | (12,609)–(988,635) | Echte Status-/Fehlermeldungen |

Oben höchstens feine bündige Leiterzüge innerhalb der **äußeren Zwischenstreifen** oder außerhalb der Sperrbereiche; keine erhabenen Komponenten. Keine ISA-Goldfinger auf dem unteren Statusfeld. Ein vollständiger ISA-Steckrand wäre nur als separate Gehäuseverlängerung denkbar und benötigte eine neue, getestete Fenstergeometrie.

## MAIN: zusätzliche komponentenfreie Montageflächen

| Element | Sperrrechteck (x1,y1)–(x2,y2) | Details |
| --- | --- | --- |
| Reverb-Sektion | (250,326)–(413,566) | Reverb-Titel, SEND-Regler + Label/Wert, kleiner Reverb-Typwahlschalter |
| Chorus-Sektion | (478,326)–(643,566) | Chorus-Titel, SEND-Regler + Label/Wert, kleiner Chorus-Typwahlschalter |
| Master-Titel | (690,326)–(959,369) | Große, gut lesbare Beschriftung |
| Master-Drehbereich | (704,359)–(882,505) | 112-Pixel-Master bei (736,372)–(848,484), plus Hand-/Ringfreiheit |
| Master-Wert | (730,489)–(857,538) | 100%-Anzeige und Bewegungsabstand |
| Hinweis | (24,554)–(263,592) | FX-SEND-Hinweis am unteren linken Rand |

**Zulässige MAIN-Dekorationsinseln (nur MAIN, niemals im globalen Faceplate):**
- **Chip-Bereich links:** (30,335)–(230,541). EMU8000-Chip mit realistischer IC-Silhouette, geringer Bauhöhe, Pins, Lötpads; feine Traces laufen in freie Umgebung. Nicht unter den FX-SEND-Hinweis bei y≥554.
- **Zwischen Reverb/Chorus:** (423,381)–(468,493). Nur kleine SMD-Bauteile und sanfte Traces, keine großen Elektrolytkondensatoren.
- **Zwischen Chorus/Master:** (650,382)–(689,499). Nur kleine Bauteile/Traces.
- **Rechts vom Master:** (899,389)–(966,508). Kleine 3-D-Bauteile mit Abstand zum Drehknopf; keine Überlappung von Master-Titel/Wert.
- **Unter Master:** (686,548)–(969,590). Niedrige Beschriftungen/Lötpads/Traces; kein hervorstehender Kondensator, der die Wertanzeige oder untere Statuszeile verdeckt.

Alle Dekorationsinseln sind **Obergrenzen**, keine Pflicht zur Vollbelegung. Mindestens ca. 10 px Abstand vom tatsächlichen grafischen Bauteilschatten zur nächsten Montagezone; bei hohen Bauteilen entsprechend mehr.

## EDIT: zusätzliche Sperrflächen

- **AMP-Überschrift:** (20,314)–(410,355); **MOD RESET:** (829,313)–(978,369).
- **AMP-Reglerreihe:** vier Gruppen um die native Regleroberkante y=363 und x=131/351/571/791; jede Gruppe inklusive Text/Wert bis y=466, x jeweils **Regler-x minus 27 bis Regler-x plus 109**. Diese ganzen Gruppen sind frei von Elektronikbauteilen zu halten.
- **FILTER-Überschriften:** (20,457)–(616,489) und (660,457)–(977,489).
- **FILTER-/TONE-Reglerreihe:** sechs Gruppen um Regleroberkante y=483, x=79/229/379/529/679/829; jede Gruppe inklusive Text/Wert bis y=590, x jeweils **Regler-x minus 27 bis Regler-x plus 109**.
- Für EDIT bleiben nur kleine Restflächen/Traces zwischen diesen Montagezonen. **Keine großen 3-D-Chips oder Kondensatoren** auf dieser Bedienseite.

## BROWSER: zusätzliche Sperrflächen

- Filter, Suche und Eingabefelder: (20,314)–(977,365).
- Scrollbare Presetliste inklusive Scrollbar, Auswahlzeile und leerem Zustand: (18,368)–(979,601).
- Nur die äußeren PCB-Rahmen dekorieren; die komplette Liste bleibt maximal lesbar.

## Geometrie-/Qualitäts-Gates vor Grafikintegration

1. Geometrie aus `src/vst3/PresetBrowserView.cpp` ist maßgeblich; bei Änderungen an der realen Bedienung dieses Dokument vorher aktualisieren.
2. Keine IC-/Kondensator-/Widerstand-/Schalter-Kollision, inklusive 3-D-Schlagschatten, Text und Menüauswahl. Auf `EDIT` und `BROWSER` darf keine MAIN-only-Grafik sichtbar sein.
3. Keine eigenmächtige Verschiebung/Verkleinerung von Kontrollen, um ein dekoratives Bauteil unterzubringen.
4. Das originale 125A-Branding aus `125A-Branding`, echte LCD-Werte und aktueller Status werden weiterhin live gezeichnet und nicht auf eine tote Bitmap gebacken.
5. Vor Freigabe: 1000×640-Screenshots aller drei Ansichten prüfen, Mausdrag und Ctrl-Reset aller 13 Regler, echte FX-Typauswahl, alle Menüs/Buttons, Browser-Suche und Status/DAW-Automation erneut nachweisen.
6. Zoom/Resize bleibt ein separater technischer Auftrag mit eigener Host-Größen-/Hit-Test-Prüfung. Kein Zoom-PASS durch bloße Vergrößerung eines Bildes.

**Abnahme dieses Schritts:** Die *Artwork-Geometrie* und der durchgehende Abstand der Elektronik zu den Control Islands sind dokumentiert. **Eine echte PCB-Grafik ist noch nicht integriert oder visuell validiert.**
