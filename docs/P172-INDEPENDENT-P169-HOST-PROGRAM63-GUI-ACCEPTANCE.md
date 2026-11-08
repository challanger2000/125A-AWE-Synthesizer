# P172 – unabhängige GUI-Gegenprobe für fehlende SF2-MIDI-Programme

**Technischer Befund:** P169 beseitigt im tatsächlich ausgeführten Windows-VST3 die falsche sichtbare Auswahl des ersten vorhandenen Instruments, wenn der Host eine im SoundFont nicht existente Programmnummer liefert. Ein altes *unverändertes* VST3 reproduziert denselben Fehler mit identischem Fixture. **NUR dieser konkret geprüfte, beim Editor-Öffnen gesetzte Programmwechsel hat PASS. Kein Gesamt-Release.**

## Herkunft / exakte Quelle

| Rolle | Revision und auf demselben Windows-Runner geprüfte Binärdatei |
| --- | --- |
| Fehlerreferenz | P168 `8ad695055cdaa0dafc99e3b1d1d61b83d9f30f14`, Actions `42435400626`, Artefakt `P168-LCD-Fix-Windows-x64-VST3-TEST`; DLL SHA-256 `8bd300bd7019efd7f7652b4393df075209944fcbd027d8b104699d96dcc7e3c7` |
| Korrekturkandidat | P169 `99fb90fc855c4c7643e24816fa644fdc738c290f`, Actions `42438260642`, Artefakt `P169-Unavailable-Preset-Windows-x64-VST3-TEST`; DLL SHA-256 `4aa865c53de76eb5e23696e7455d9c1e7708438ffee8f83a35e1fd22c62125cb` |
| Unabhängiger generischer Host | `125A-Plugin-Test-Lab`, Branch `audit/p98-real-host-param-gui-p169`, SHA `fb5a8e997e4148f51cf784b8e2b6a712435f0f3e`; echter, aus Quelle gebauter Win32-VST3-Host, kein Produktcode importiert |
| Unabhängiger Prüfvertrag | AWE-Branch `audit/p172-independent-external-program-gui`, Test `tools/p172_host_program_visual_oracle.py` SHA `9ff7e031b0cb9c30153f3f89db0870dddba3b861`, Windows Actions [`42440052388`](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42440052388): **SUCCESS** |
| Unveränderte Produktquellen | Keine produktive Codeänderung im P172-Prüfbranch; P169 blieb unverändert und offen als [Draft PR #84](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/84) |

**Originalnachweise:** GitHub-Artifact [`P172-Independent-Actual-Host-Missing-SF2-Program63-Visual-Evidence`](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42440052388/artifacts/13600919202), inklusive der 8 tatsächlichen Win32-`GetDIBits`-BMP-Screenshots `p168/step-{0..3}.bmp`, `p169/step-{0..3}.bmp`, `host-values.tsv`, `P172-RESULT.json`, Provenienz und der öffentlich redistributierbaren synthetischen SF2. Der Workflow vergleicht exakte SHA-256-Werte von **beiden** Binärdateien vor dem Test. Er meldet bei falscher Identität oder fehlendem Screenshot FAIL.

## Unabhängiges akustikfreies Orakel

Die synthetische SoundFont enthält in SF2-Bank 0 die real existierenden **Programme 0 und 12**, aber **nicht 63**. Der generische Windows-VST3-Host setzt den realen automationsfähigen `ParamID 1000` zunächst auf 0, dann auf 12/127, dann auf 63/127 und schließlich auf 0; der Host liest und prüft die tatsächlich akzeptierten Controller-Parameterwerte. Für jeden Wert wird danach ein **frisch angehängter echter VSTGUI-Editor** erzeugt und dessen tatsächlich angezeigter Hardware-Presetselector (logisch x279..511, y241..266) mittels Win32-`BitBlt`/`GetDIBits` aufgenommen.

**Geometrie:** Der originale P165/P169-Editor ist 1000×708; seine physische Presetleiste liegt bei y234..273. Die ersten beiden Auditversuche verglichen versehentlich die **alte** um 55px zu hohe P164-Koordinate y186..212. Dort war das Bild per Definition unverändert; der Fail-Closed-Test gab korrekt **FAIL**. Die anschließende Behebung der *Testkoordinaten*, nicht des Produktcodes, wurde anhand echter Original-BMPs unabhängig geometrisch gegengeprüft.

| Konkrete Gegenprobe | Originaler P168-FEHLER | Korrigierter P169 |
| --- | --- | --- |
| Programm 0 → existierendes Programm 12 | **590** veränderte Textpixel, PASS Positivkontrolle | **590** veränderte Textpixel, PASS |
| Programm 0 → fehlendes Programm 63 | **0** Textpixel, weiterhin irreführend „000 125A PIANO“ (**negativer Originalcode-Oracle**) | **720** Textpixel, „063 NICHT VORHANDEN“ (**PASS**) |
| Programm 63 → gültiges Programm 0 | **0** Restabweichungen, PASS | **0** Restabweichungen, PASS |

**Falsifizierbarkeit:** Wird P169 durch die **originale** P168-DLL ersetzt, schlägt die geforderte Abwesenheitsanzeige messbar fehl, obwohl die valide Programm-12-Positivkontrolle weiterhin beweist, dass der Host echte Programmänderungen anzeigen kann. Die unabhängigen Erwartungen wurden aus der bekannten SF2-Presetmenge `{0,12}` und dem Nutzervertrag abgeleitet, **nicht** aus dem P169-Produktcode. Ein Test, der weder 12 noch 63 auf dem Bildschirm unterscheiden kann, darf niemals PASS melden.

## Abgrenzung: Was wirklich PASS und was NOT RUN ist

| Prüfobjekt | Endstatus | Beweis und Grenze |
| --- | --- | --- |
| Host-Programm **63**, bevor echter GUI-Editor geöffnet wird | **PASS** | Windows P172 mit echten P168-/P169-Binärdateien und visuellen Pixelausgaben |
| Bestehende Programme 0,12 und Wiederherstellung 0 | **PASS** | 590/590 positive, danach 0/0 Restabweichung |
| P169 allgemein kompilierbar / native CTests / Validator / GUI-Basistests | **PASS, beschränkt** | [Windows #42438260642](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42438260642): 47/47 CTests, 537/537 Steinberg Validator, EditorHost 3×, 99/99 native GUI-Interaktionen; das beweist nicht die restliche musikalische Funktion |
| Programm 63 per Host-Automation **während** Editor offen | **INCONCLUSIVE / NOT VERIFIED** | Der zusätzliche generische Test-Lab-Versuch `--capture-host-param-sequence` akzeptierte die Host-Parameterwerte, aber dessen laufender Editor zeichnete **auch für gültiges Programm 12 nichts neu**; die Positivkontrolle versagte. Die Ursache im generischen Host-/Runloop-/UI-Idle-Vertrag ist ungeklärt. Kein Produkt-FAIL oder PASS daraus ableiten |
| Native Popup-Menühervorhebung bei Programm 63 | **NOT RUN** | Der geschlossene echte Presetselector ist bewiesen; die native Windows-Menüöffnung während Hoständerung wurde nicht gesondert pixelgetestet |
| MIDI-Ereignis/Processor/PCM/ROM/SF2-Bankklang | **NOT RUN in P172** | Separat validierte P166-Bereiche, aber der belegte P167 MIDI-Kanal10-CC0-Bankfehler bleibt **FAIL** |
| Originale private SF2/Wave-ROM, tatsächliche Anwender-DAW, physisches ASIO | **NOT RUN** | Keine Originaldateien im öffentlichen Testartefakt, keine echte Audio-/Hardwareabtastung |
| Vollständiger Adversarialer Source-/Test-/DSP-/Host-Audit | **NOT COMPLETE** | P172 ist ein **eingegrenzter unabhängiger visueller Funktionsaudit**, kein FULL AUDIT |

## Schluss

**P169 Browser-Anzeige bei Editor-Neuöffnung: PASS**, unabhängig vom Korrekturautor verifiziert. **Alle anderen offenen Audio-, MIDI-, Live-Automations-, Original-ROM- und Release-Gates bleiben unverändert.** P169 [Draft PR #84](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/84) darf erst nach Integration aller notwendigen Produktkorrekturen und Eigentümerabnahme gemergt werden. P172 war ein reines Audit und enthielt keinerlei Produktionscode-Änderung.
