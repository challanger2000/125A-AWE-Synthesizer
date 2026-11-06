# P129 – bitidentische CPU-Optimierung des ROM-gestützten 86Box-EMU8000

**Basis:** P128-Produktion `a897d84c0cdafc91fe4e2e7550e10f88c2455b93` (P128-MIDI-/Bank-/Save-Fehler korrigiert). **Kein Chorus-DSP-Rundungswechsel** in dieser Änderung.

## Ursache und Änderungen

Beim Rendern mit der echten `Emu8000Box`-86Box-Chipengine ruft `Emu8000Core::RenderBlock` aus Gründen der Treiberregister-Buchführung zusätzlich den alten `RenderNative`-Floatpfad auf.

1. Die dort pro Frame berechneten Floating-Point-**Chorus-, Reverb- und EQ-Returns** gelangen unter `Chip::Box86` **nicht** an den VST3-Audioausgang, denn `m_box.RenderFrame` ersetzt dessen PCM vollständig. Nur diese unbenutzte zusätzliche FX-Berechnung wird bei Box86 ausgelassen. Die alte **Voice-, Clock- und Registerbuchführung** bleibt weiterhin aktiv. Für den eigenen Legacy-Chipmodus bleibt das Verhalten unverändert.
2. `UpdateRegistersFromState` berechnete für jede der 32 Stimmen pro native Frame erneut `pow(2, IP)`, sogar ohne Änderung des IP-Registers. Der **Bit-genau identische Formelwert** wird pro VoiceState unter dem tatsächlichen 16-bit-IP-Schlüssel gespeichert und nur bei einer IP-Änderung neu berechnet. Der abgeleitete Registerspiegel `CPF` wird nach wie vor **bei jedem Frame** aktualisiert; kein Hardware-IO und keine Zustandsserialisierung werden entfernt.

Weder das echte 86Box-Sample-/Filter-/Chorus-/Reverb-/EQ-Verhalten noch der Treiberbefehlspfad werden durch diese beiden Änderungen absichtlich verändert.

## Unabhängige Windows-A/B-Nachweise

Jeweils **zwei getrennte Original- und Kandidatenläufe** auf demselben Windows-2022-Runner (Reihenfolge Original–Kandidat–Kandidat–Original), identischer öffentlich synthetischer ROM/SF2-Fixture, 44,1 kHz und pro Szenario 400 echte Renderaufrufe. Kontrolle des vollständigen **PCM-FNV64** sowie der **acht gespiegelten EMU8000-Register aller 32 Stimmen** nach jedem Szenario, einschließlich 128/1024 Samples, 1/16/30 Noten und dichter Pitchbend-Automation.

- Nur nicht verwendete Legacy-FX übersprungen: [CI #42176121228](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42176121228): **8/8 bitidentisch**, Leistungsgewinn ca. 2 % bei 30 Stimmen, ca. 7 % bei 1 Stimme.
- Nur IP-Registercache: [CI #42176974697](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42176974697): **8/8 bitidentisch**, ca. 35–36 % bei 1 Stimme, 7–9 % bei 16 Stimmen, 0–4 % bei 30 Stimmen.
- **Beide Änderungen gemeinsam**: [CI #42177504236](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42177504236), **8/8 bitidentisch**, einschließlich exakter Register-Mirror-Signaturen.

| Last | Original Mittelwert | P129 kombiniert | Beschleunigung |
|---|---:|---:|---:|
| 1 Stimme, 128 Frames | 0,2842 ms | 0,1517 ms | 46,60 % |
| 1 Stimme, 1024 Frames | 2,2541 ms | 1,1789 ms | 47,70 % |
| 16 Stimmen, 128 Frames | 0,7840 ms | 0,6660 ms | 15,06 % |
| 16 Stimmen, 1024 Frames | 5,9536 ms | 5,3232 ms | 10,59 % |
| 30 Stimmen, 128 Frames | 1,1875 ms | 1,1213 ms | 5,58 % |
| 30 Stimmen, 1024 Frames | 9,6334 ms | 9,1746 ms | 4,76 % |
| 16 Stimmen + Pitchbend, 128 Frames | 0,7760 ms | 0,6950 ms | 10,43 % |
| 16 Stimmen + Pitchbend, 1024 Frames | 6,0533 ms | 5,5336 ms | 8,58 % |

Diese Zeiten sind *ein einzelner verschränkter Windows-GitHub-Runner-Test* und dürfen nicht als garantierte ASIO-Deadline oder Leistung eines bestimmten PCs interpretiert werden.

## Abnahmegrenzen

- [Getrennter vollständiger Windows-Cache-Test #42176974744](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42176974744): **40/40 CTests, 47/47 VST3-Validator und 3/3 EditorHost-Smokes**.
- Der vollständige Windows-Gesamttest *beider Änderungen gemeinsam* ist unter [CI #42177504122](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42177504122) dokumentiert (Resultat vor Merge nachprüfen).
- Die beiden A/B-Harnesses und Rohdaten liegen auf separaten Audit-Branches, **nicht** im finalen Verkaufs-Plugin.
- Die bereits vorher unter Realzeit-Stresstests gefundenen sporadischen Überschreitungen auf geteilten Windows-Runners sowie die ASIO-Abnahme auf dem Zielrechner bleiben eigenständige Gates, siehe [Issue #66](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/66).
- Die aktuelle Chorus-Rundungs-Hardwaretreue aus [Draft PR #67](https://github.com/challanger2000/125A-AWE-Synthesizer/pull/67) ist **nicht Bestandteil** dieses P129-CPU-Fixes.

**Trotz bitgenauem A/B-Test ist dies keine vollständige Hardware- oder DAW-Releaseabnahme.**
