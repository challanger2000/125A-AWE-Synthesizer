# P173 – Host-Automation während bereits geöffneter VST3-GUI

**Ergebnis: INCONCLUSIVE für Produktursache, GUI-Verhalten im generischen Test-Lab: FAIL. Kein FULL AUDIT, kein Release-PASS.**

## Exakt geprüfter Stand

- P168 Fehlerreferenz `8ad695055cdaa0dafc99e3b1d1d61b83d9f30f14`, Windows-geprüfte DLL SHA `8bd300bd7019efd7f7652b4393df075209944fcbd027d8b104699d96dcc7e3c7`.
- P169 Anzeige-Fix `99fb90fc855c4c7643e24816fa644fdc738c290f`, DLL SHA `4aa865c53de76eb5e23696e7455d9c1e7708438ffee8f83a35e1fd22c62125cb`.
- Unabhängiger generischer Test Lab Win32 Host `audit/p99-live-host-gui-timer`, `9523aab9e4c29618d037b285ad33ee57e1926460`, *mit* dem von Steinberg vorgeschriebenen `IEditController::setComponentHandler`.
- Windows [P173 Run #42441305213](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42441305213) **FAIL** wegen nicht erfüllter Positivkontrolle; [Rohdaten und acht native Win32-Screenshots](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42441305213/artifacts/13601013726).
- Kontrollvergleich P172 [SUCCESS #42440052388](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42440052388), wenn der Wert **vor Editoröffnung** gesetzt wird. P172 bleibt PASS für genau seinen Geltungsbereich.

## Ablauf und Falsifizierbarkeit

Eine eigenständig erzeugte SF2 enthält Bank0-Programme 0,12, aber nicht 63. Der Host hält den *gleichen echten* VSTGUI-Editor geöffnet, setzt echten Controller ParamID1000 nacheinander auf 0/127, 12/127, 63/127, 0/127 und prüft nach jedem Aufruf `getParamNormalized` sowie 1,3 Sekunden echten Win32-Messageloop. Ein korrektes Ergebnis müsste für **gültiges Programm12** sichtbare Änderung im Presetfeld zeigen und für **fehlendes Programm63** in P169 ausdrücklich „063 NICHT VORHANDEN“. Der Test prüft tatsächliche `GetDIBits`-BMP, keine Source-Regex oder simulierte Oberfläche.

**Beobachtet:** Beide unveränderten Originalprodukt-DLLs akzeptieren alle vier Werte; der Lab-Thread verarbeitet pro Wert ca. 60–62 `WM_TIMER`-Callbacks und mindestens einen `WM_PAINT` nach Wertwechsel. Trotzdem bleiben sämtliche vier **vollständigen 1000×708-Screenshots innerhalb jeder DLL byteweise pixelidentisch** – auch LCD und native Presetleiste. Somit schlägt bereits die **gültige Program12-Positivkontrolle** fehl. Dieser Test kann aktuell nicht beweisen, dass P169-Live-Update defekt oder korrekt ist. Entweder ruft das angehängte Produktfenster sein `PresetBrowserView::onIdle()->Sync()` nicht auf, die angehängte View empfängt nicht denselben Controllerwert oder der generische Testhost bildet ein weiteres VST3-UI-Hostdetail unvollständig nach. Ursache und echte DAW-Reproduktion ungeklärt.

**Wichtig:** Ein erster P173-Lauf ohne gesetzten `IComponentHandler` war nicht vollständig hostkonform; er wird als fehlerhafte Testumgebung verworfen, *nicht* als Produktfehlbeleg. Für den zweiten Lauf wurde ein gültiges `IComponentHandler` mit `beginEdit/performEdit/endEdit/restartComponent` registriert. Das Testergebnis blieb in diesem Fall unverändert. Der Test erzeugte *keinen* Host-MIDI-NoteOn und beweist keine Audio-/Bank-Korrektheit.

## Offene QA-Gates

| Kette | Status |
| --- | --- |
| Host-Parameter bei Editor-**Neuöffnung** (P172) | PASS: vorhandenes Programm12, fehlendes63, Rückkehr zu0, unveränderte Fehlerreferenz als rote Gegenprobe |
| Host-Parameter bei **bereits geöffnetem Editor** (P173) | INCONCLUSIVE: Positivkontrolle fehlgeschlagen, beide Versionen reagieren visuell nicht im generischen Host |
| Tatsächlicher DAW-Host-Callback/GUI-Automation | NOT RUN für diesen spezifischen Fall |
| Original-ROM/SF2-PCM, P167 Kanal10-Bankfehler, gesamtes Plugin | Nicht Gegenstand P173; kein Release-PASS |
| 125A Engineering FULL Audit Completeness Contract | NICHT ERFÜLLT durch diesen eingegrenzten Test |

## Weiteres Vorgehen

Die Ursache isolieren, bevor irgendein Produkt-Fix behauptet wird: `PresetBrowserView::onIdle` und `Sync` auf *einem ausschließlich testinstrumentierten Branch* sichtbar zählen, Controllerwerte innerhalb von `Sync` protokollieren, unabhängig durch native UI-Click-Positivkontrolle und vergleichbaren echten DAW-Host absichern. Keine Änderungen an Codex P170/P171, Produkt-`main` oder Originaldateien aufgrund einer unbestätigten Host-Testhypothese.
