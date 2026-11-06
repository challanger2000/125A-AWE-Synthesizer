# P141 – Funktionale AWE-VSTGUI abgeschlossen; Hardware-Gestaltung als nächster Schritt

**Stand:** 6. November 2026. **P141 vollständig in Entwicklungsbranch `fix/p122-bank-dirty-audit` gemergt:** [PR #78](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/78), Merge-Commit `fe37940e81ffc7427b4a71f967964ce4a1da2193`.

**Letzter exakt vollständig geprüfter P141-Quellstand:** `e03cd9f2dd47c2afdbaa347be7f85af2b738eb09`, [vollständiger Windows Actions #42247386531 – SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42247386531).

## 1. Erst funktionierende VSTGUI – durch echten Windows-Editor bestätigt

Der tatsächliche native Steinberg-VSTGUI Editor `PresetBrowserView` bleibt ein kontrollierbares, **funktionierendes** 1200×780-Layout und wird nicht durch das visuelle Referenzbild ersetzt. Der neue P141-Test startet `editorhost.exe` auf einem tatsächlichen Windows-Desktop größer als 1400×900 und bedient mit Maus, Tastatur und Win32-Nachrichten alle wesentlichen Komponenten.

| Funktion | P141-Abnahmekriterium |
| --- | --- |
| Alle 12 SoundFont-Klangparameter (AMP 4, Filter/Tone 6, Reverb-/Chorus-Send 2) | Jeder Regler einzeln per echtem Mausdrag auf Wert >0, in Pixeln nachgewiesen; **Ctrl-Klick** wieder auf neutrales 0 %, Ausgangsanzeige gleich |
| Master Volume | Reagiert auf Drag; eigener Ctrl-Klick stellt **100 % Unity** wieder her |
| Reverb Type, Chorus Type | Beide achtfachen **Original-Creative-Preset-Dropdowns** ändern nach Tastaturauswahl sichtbar den aktiven Modus |
| Bank/Program, Browser | Synthetische SF2 mit Bank 0 Programmen **000 (Piano)** und **012 (Synth Brass)**, Bank 2 Program 004, Bank 128 Drumkit; **NEXT/PREV** ändern die tatsächliche Presetauswahl, Suchfilter und Browsertabelle reagieren und bleiben synchron |
| ROM-Laden/SF2-Laden | Native Win32-Dateidialoge öffnen und lassen sich **ohne Mutation der bisherigen Auswahl** abbrechen; echte ROM-Ladeakzeptanz benötigt weiterhin die vorhandene gesonderte Prozessor-/Asset-Regression |
| Reset | Neu eindeutiger **MOD RESET** für nur zwölf SoundFont-Offsets, nicht für Master/Bank/FX/geladenes ROM |
| Bankfilter | Rechte Browsertabelle heißt **FILTER**, zur Unterscheidung von der aktiven Bank links |
| Editor-Lebenszyklus | Öffnet 1200×780 und schließt ohne Crash; Browser lässt sich an- und abschalten |
| DAW-Automation | Host-Edit `beginEdit`/alle `performEdit`/`endEdit` bilden eine **zusammenhängende Geste pro Mausdrag**, keine zig verschachtelten DAW-Automations-Touches |
| Host-Parametertexte | Tatsächlich exportierter VST3-Controller zeigt **Room 1/2/3, Hall 1/2, Plate, Delay, Panning Delay; Chorus 1/2/3/4, Feedback, Flanger, Short Delay, Short Delay + FB**, inkl. automatisierbarer ParamIDs 1200/1201, exakt acht normalisierte Host-Index-Roundtrips und unveränderte Creative-Defaults **Hall 2/Chorus 3** |
| Projektrecall | Unveränderte V11-/Legacy-Migration aus der AWE-Testmatrix, keine Schema-/DSP-Codeänderung |

Der neue **`awe32_p141_vstgui_host_names_test`** lädt den VST3-Controller aus dem **tatsächlich gebauten DLL-Factory-Export**, statt Quelltext-Etiketten zu vergleichen.

### Unabhängige vollständige Windows-Build-/GUI-Prüfung

[Windows-2022-Action #42247386531 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42247386531), gepinnt auf `e03cd9f2dd47c2afdbaa347be7f85af2b738eb09`:

- **45/45** vollständige CTests, einschließlich P141 alle 16 FX-Namen, V11-State, P133/P134 Audio-/CC120 und vorherige Regressionen.
- **537/537** vollständige echte Steinberg-VST3-Modulvalidator-Prüfungen.
- **3/3** bisherigen tatsächlichen Windows-EditorHost-Smokes.
- **59/59** neue physische P141 GUI-Interaktionen, darunter **12× Regler Drag + 12× Ctrl-Reset + 12× tatsächliche Rückkehr zur 0%-Anzeige**, alle FX-Mode-Menüs, Programm-PREV/NEXT, Search/Bank-/Dialogabbruch und Master.
- Original-GUI-BMPs, vollständige Testergebnisse und Host-Log sind im Actions-Artefakt **`P141-VSTGUI-Complete-Controls-FX-Preset-Windows-Regression`** archiviert. Das *tatsächlich gebaute, technisch geprüfte* Windows-x64-VST3-Testpaket im Artefakt **`P141-VSTGUI-Functional-Windows-x64-VST3-TEST`** ist **kein Release/Gumroad-Paket**.
- **Unveränderte P137-Audioengine.** Daher bleiben ihre unabhängigen [P139 0/201.600 Deadlinefehler](docs/P139-P140-WINDOWS-REALTIME-ABNAHME.md) und der vollständige Produkt-/Test-Lab-P53-Befund maßgeblich; P141 selbst ist eine separate UI/Host-Gesten-Regressionsprüfung.

## 2. Danach die hardwareinspirierte Designphase, wie vom Nutzer gewünscht

**Die vom Nutzer im Chat gezeigte Bildreferenz `125A AWE Synthesizer Hardware-Panel(1).png` ist ausdrücklich ZIELGESTALTUNG, keine schon gelieferte GUI oder verpflichtende Pixelkopie.** Die Entscheidung ist: **funktionierende native VSTGUI zuerst** (P141 abgenommen), danach ein **hochwertiges schwarzes/goldenes Hardware-Frontpanel**.

Visuelle Leitplanken der Bildreferenz:
- Dunkles Metallgehäuse, präzise goldene PCB-Leiterbahnen und dezente Schraubenköpfe; EMU8000-Synth-Chip als Hardware-Element. Kein kitschiger LED-/Plastiklook.
- Bernsteinfarbiges Status-LCD mit **echten** EMU8000-, ROM-, SF2-, Bank-, Programm- und gegebenenfalls Pegelzuständen; Statuslampen niemals ohne die entsprechende verifizierte Engine-/Host-Rückmeldung dauerhaft grün zeichnen.
- Klare Hierarchie: **MASTER VOLUME** als Hauptregler; **HALL/CHORUS** als getrennte tatsächlich veränderbare Send-/Lautstärkeregler. Die dazugehörige **Reverb-Type/Chorus-Type**-Auswahl muss weiterhin vollständig zugänglich bleiben.
- Große, gut lesbare **PRESET**- und **BANK**-Auswahl. **ROM LOAD**, **SF2 LOAD**, **BROWSER** und **MOD RESET** als echte Bedienelemente; der rechte Presetbrowser muss auch weiterhin nach Bank filtern und nach Namen suchen können.
- Die zwölf **zusätzlichen** SoundFont-Envelopes/Tone/Sends dürfen **nicht** zugunsten der drei dominanten Regler aus der Bedienbarkeit verschwinden. Für die visualisierte Hauptfläche ist eine klare **ADVANCED**-/Edit-Sektion sinnvoll, mit uneingeschränktem Host-Parameterrouting und ohne unnötige mehrstufige Menüs.
- Als technische Realisierung VSTGUI-CViews/CControls und UI-/Host-State, nicht bloß ein statisches PNG mit unsichtbaren oder unzutreffenden Hotspots. Die aktuelle 1200×780 Testgeometrie dient als verifizierte Funktionsbaseline.
- UI-Aufbau zuerst als echte kontrollierte Objekte, anschließend Styling und vollständige Wiederholung von P141 einschließlich Window-Koordinaten und Controller-Gesten. Niemals funktionierende Bank-/Preset-/MIDI-/V11-Speicherung beschädigen.

**Nicht mehr als Release-Blocker verfolgen:** 1:1-Originalhardware-Chorus-Rundungsparität (explizite Nutzerentscheidung). **Weiterhin nicht als durchgeführt behaupten:** echter physischer Zielrechner-ASIO/kommerzielle DAW-/MMCSS-Test und finale Paketfreigabe. Windows-Funktions-/Echtzeitlabor ist grün, aber kein Ersatzbeweis für eine nicht ausgeführte reale Treiber-/DAW-Sitzung.
