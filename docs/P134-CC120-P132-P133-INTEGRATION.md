# P134 – CC120 physische Chip-Stummstellung, P132-F01 und P133-V11 integriert

**Stand:** 2026-11-06; **Entwicklungsbranch:** `fix/p122-bank-dirty-audit`  
**[PR #73 gemergt](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/73)**, produktiver Merge-Commit `747f221284559919331ed0aea2ae74f7b1b46418`.  
**Vollständiger geprüfter Quellstand:** `f4eb2a699122d70f3dd889fd747de20022064ab4`, [Windows Actions #42221403709 – SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42221403709).

**Urteil:** CC120-Funktionsfehler **PASS**, 980-Frame-Produktfix **integrationstechnisch PASS**, 8×8 FX + V11-State/Audio bitidentisch zur P133-Basis; **REALTIME weiterhin NO-GO / RELEASE-NO-GO**, echter ASIO-Test NOT RUN. Kein Gumroad-Paket.

## 1. Negative Reproduktion des CC120-Produktfehlers

Die neue tatsächliche ROM-gestützte SDK-Processor-Regression `125A_p134_cc120_physical_stop` ist vor der Korrektur auf Windows absichtlich ROT: [Run #42220437871](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42220437871). 43/44 CTests PASS; exakt der neue CC120-Fall FAIL.

Nach einem hörbar klingenden NoteOn auf Kanal 0 und CC120 (`All Sounds Off`) verbleibt nach einer ausgerenderten Hardware-FIFO-/Release-Wartezeit in den letzten 4×1024 Frames **21,3853** aufsummierte PCM-Quadratenergie. Die gleiche Test-DLL lässt eine neue Note weiterhin zu und spielt einen anderen MIDI-Kanal, obwohl die zuvor gestoppte Stimme noch ein Lautstärkeziel besitzt. Dies passt zum separaten, im [P132-Auditbericht](docs/P132-REALTIME-AUDIT.md) auf dem ursprünglichen Code gezählten Chipzustand: 0 belegte Synth-Slots, 1 nichtstumme 86Box-Stimme bei abgeschalteter Volume-Envelope.

**Ursache:** Der vorhandene `KillVoice()` schreibt nur `DCYSUSV = OFF`; der 86Box-DSP verfolgt aber `vtft_vol_target` und `cvcf_curr_volume` unabhängig vom Envelope-On-Flag. Bei weiterhin positivem Ziel bleibt die alte Stimme dauerhaft klingend. Dies ist keine reine Scheduler- oder GUI-Fehlmessung.

## 2. Gezielte Codekorrektur und Negativ-Orakel

Im Win95-VST3-CC120-Zweig von `Synth::ControlChange()` werden nun nur zuvor wirklich belegte Stimmen **des entsprechenden MIDI-Kanals** bearbeitet (`age != 0`, `channel` stimmt):

1. Das bisherige `KillVoice(i)` setzt `DCYSUSV=OFF`.
2. `m_core.Write(Reg::IFATN,i,0x00FF)` setzt den realen Chip-Lautstärkezielwert über die bestehende `attentable[255] = 0` auf null.
3. Der unveränderte, am Hardwareverhalten kalibrierte 1/64-Volumenschliff führt das aktuelle Volume sauber nach null, statt einen künstlichen DSP-Reset oder eine neue globale Stummschaltung einzuführen.

`KillVoice()` selbst, Stimmenstehlen, der DOS-MDI-Driverpfad, CC123 (All Notes Off), NoteOff und das Reverb-/Chorus-DSP bleiben unverändert. Keine zusätzlichen Heap-Allokationen, Mutex, Threads oder neuen User-Schalter im Echtzeitpfad.

Der gleiche Test prüft nach CC120 **späte digitale Stille (Quadratenergie ≤ 1e-8)**, erfolgreiches erneutes NoteOn desselben Kanals und hörbaren Fortbestand eines nicht adressierten Kanals. **Windows-P134-Funktionstest PASS**.

**Grenze:** Dies ist ein implementiertes, reproduzierbar getestetes Stop-Verhalten der Emulation, kein Beweis für jedes interne Registerübergangsdetail einer realen EMU8000-Karte. Die 980-Frame-Audio-FIFO-Latenz und die Effekt-Tails werden nicht willkürlich auf null zurückgesetzt.

## 3. P132-F01-Renderkorrektur sauber auf P133 übertragen

Von `audit/p132-realtime` wurde **nur** die gezielt belegte Produktionsänderung in `src/engine/Emu8000Box.cpp` in den aktuellen Entwicklungsstand übernommen:

- Nach 128, 256, 384, 512, 640, 768 und 896 verarbeiteten Chipframes `AdvanceChip(frameInBlock)`; bei 980 Frames unveränderte FIFO-Veröffentlichung.
- Derselbe echte `emu8k_update()` und dieselben Registerwrites in gleicher Reihenfolge, ursprüngliche Frameoffsets, gleiche FIFO-DSP-Berechnung und Effekte.
- Keine Änderung an `snd_emu8k.c` (also **kein** unbewiesener Signed-Chorus-DSP-Fix), der ursprünglichen Sample-Interpolation oder P133-Effektparametern.

Originale P132-Labor-Messung nach dem einen Eingriff: **90/12.000 → 2/12.000** Deadlinefehler in den konstanten 128-Frame-/30-Stimmen-Render-Crossovers auf denselben zwei Windows-Runners. Der Median wurde dabei absichtlich etwas höher, da Rechenarbeit verteilt wurde, nicht ausgelassen. Dieser reproduzierte Fortschritt begründet den Produktionsport, **nicht** eine Echtzeitfreigabe.

## 4. Unabhängiger V11-Bitidentitätsnachweis (echte VST3-DLLs)

Nicht nur Engine-Einheitstests: Die **exakte unveränderte P133-V11-Preview-VST3** aus dem erfolgreichen Windows-Run [#42196456180](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42196456180) wurde per GitHub-API auf Quellcommit `66b3dc8277f68efb0eaa4857ab61a5cfd3d637c8` festgenagelt und auf demselben Windows-2022-Runner **als tatsächlich geladenes Modul** der aktuellen P134-Produktions-DLL gegenübergestellt.

Das neue Testprogramm `tests/p134/vst3_pcm_compare.cpp` verwendet echte VST3-Processor/Steinberg-SDK-Schnittstellen, ausschließlich synthetische ROM/SF2-Fixtures und 12 Zellen:

- Audiopuffer **128/256/512/1024 Frames** × angesetzte **1/16/30 NoteOns**.
- **256 Blöcke je Zelle**, insgesamt **3.072 Vergleichsblöcke / 1.474.560 Stereo-Frames / 11.796.480 PCM-Float-Bytes**.
- Alle **64** originalen Creative-Reverb/Chorus-Presetpaare **0..7 × 0..7** werden in echten Host-VST3-Parameterevents wiederholt automatisiert, zusammen mit Pan-/Pitchbend, MIDI-Programmen/Banken/Kanalprogrammen, reellem Reverb-/Chorus-Send, Master-/Filter-GUI-Parametern.
- Nach jedem Block ein kompletter V11-State-Snapshotvergleich; periodisch V11-Projektrecall. Ergebnis **sämtliche PCM-Floats und alle State-Snapshots exakt bitidentisch**.
- Das nun absichtlich geänderte **CC120 während aktiv spielender Noten** wird von diesem *Bitgleichheitsvergleich* ausgeschlossen. Es besitzt das separate rot-zu-grün-Regressionstest-Orakel; andernfalls wäre ein korrekter Bugfix wegen veränderter Ausgabe fälschlich ein Testfehler.
- Die verwendete V11-Standard-DLL ist wirklich die P133-GUI-/FX-Binärversion, keine historische V10-Vergleichsdatei. Diese A/B bestätigt die Integration von P132 mit P133, nicht eine neue Messung aller P132-ETW-Laufzeitpopulationen.

Das Rohprotokoll `p134-p133-fx-pcm-comparison.txt`, Pin-/SHA256-Herkunft, 3× GUI-Fensterbilder, die Gesamt-CTest-Ausgabe und Validatorprotokoll liegen im [P134-Windows-Run #42221403709](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42221403709) als Artefakt `P134-CC120-FX-V11-Windows-Full-Regression`. Das erfolgreich geprüfte, nur für Tests bestimmte VST3-Preview-Artefakt heißt `P134-AWE-CC120-FX-RT-Windows-x64-VST3-PREVIEW`.

## 5. Vollständiges Windows-Funktionsgate

**[P134 Windows-2022 x64 Run #42221403709 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42221403709)**, geprüfter Commit `f4eb2a699122d70f3dd889fd747de20022064ab4`:

| Test | Befund |
| --- | --- |
| Gesamter nativer CTest-Katalog inkl. P134 CC120, P133 64 FX und P134-A/B | **45/45 PASS** |
| Steinberg SDK-Validator-Selbsttest während des Builds | **47/47 PASS** |
| Tatsächlicher vollständiger VST3-Modulvalidator | **537/537 PASS** |
| Echte Win32-EditorHost-GUI-Smokes, jeweils mit Hardware-Panel und Bedienung | **3/3 PASS** |
| P133 vs. P134 V11 real DLL Stereo Float-PCM | **11.796.480/11.796.480 Bytes bitidentisch** |

## 6. Strikte Grenzen und weiterer Entwicklungsauftrag

**P132 Echtzeit als Ganzes weiterhin FAIL**, trotz Verteilung des beweisbaren 980-Bursts. Historische **P132-Nachher**-Messmatrix zeigte **796/172.800** Deadlineüberschreitungen; insbesondere Save/Recall und dichter Automation. In dieser P134-Funktionsregression wurde die volle mehrstündige P132/ETW-Stressmatrix **nicht** erneut für den integrierten V11-Stand ausgeführt; keinesfalls `45/45 PASS` als Echtzeit-Freigabe deklarieren.

Weiter notwendig: reproduzierbarer Ursachennachweis der noch nicht verstandenen On-CPU-Spitzen, ETW/DPC/ISR/Hypervisor-Klassifikation, Stresstest der integrierten P134-Produktions-DLL unter gleichen Stimmen, ASIO/MMCSS/DAW auf dem realen Zielrechner, physische Chorus-Fidelity-Probe (oder explizit akzeptierte Näherung) und unabhängiger Release-Gesamtaudit.

**Aktueller Entwicklungsstand darf den korrigierten CC120 und den belegten P132-F01-Renderer besitzen, aber es gibt weder Audio-Echtzeit-GO noch Gumroad-/Releasefreigabe.** Die Codex-P132-Diagnostik auf `audit/p132-realtime` bleibt als Evidenz und für spätere ETW-Auswertung unverändert.
