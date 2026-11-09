# P190 – Chorus/Reverb bei 0 % wirklich trocken (Bass-Mono)
Stand: 2026-11-09 · Entwicklungsbranch `fix/p190-zero-fx-dry`

## Nutzerbefund und nachgewiesener Implementierungsfehler

Ein ursprünglich mono abgemischter SF2-Bass klingt bei den angezeigten
Chorus-/Reverb-Reglerständen 0 ungewollt räumlich. Das entspricht
nicht dem erwarteten 125A-Bedienvertrag **0 % = AUS**.

Die tatsächliche VST3-Implementierung in
`Synth::StartLayers` addierte vorher einen positiven GUI-Betrag zum
vorhandenen SoundFont-Preset- und MIDI-Send. **Bei 0 % wurde nur keine
Zugabe vorgenommen**, aber die in `SF2` (Generatoren 15/16) oder durch
CC91/93 gespeicherten Send-Pegel blieben erhalten.
Darüber hinaus sind die echten Creative-Effektpreset-Indices 0..7
verschiedene **Effektarten**: `Chorus Type=0` ist `Chorus 1`,
`Reverb Type=0` ist `Room 1`, nicht AUS.

Der eigentliche ROM-pflichtige Produktionspfad benutzt
`Emu8000Core::Chip::Box86`. Er rendert eigene Effekte; Änderungen an
`Emu8000Fx`-Float-Workalikes würden das eigentliche Problem nicht
beheben. Hier muss der EMU8000-Register-Send selbst auf null gesetzt
werden: `PTRX[15:8]` für Hall und `CSL[31:24]` für Chorus.

## Entwicklungsfix

- Beide GUI-Controls 10/11 werden zu **absoluten Send-Level-Reglern**
  mit monotonem Verlauf. `0` schreibt den Send-Wert `0`, selbst wenn
  das Patch und MIDI einen größeren Wert verlangen; `100` erreicht
  `255`, Zwischenwerte berücksichtigen den originalen Patch/MIDI-Pegel.
- Per Voice wird der noch unbearbeitete Patch/MIDI-Send archiviert.
  So können Änderungen an den Reglern bei aktuell gehaltenen Tönen
  direkt die tatsächlichen Hardware-Register überschreiben.
- Unabhängige Register-/Matheregressionsprüfungen, echte 86Box-
  Stereo-PCM-Prüfung mit synthetischer SoundFont und absichtlich
  hohen originalen Effekt-Sends.
- Keine Veränderung der acht Creative-Effektarten/-Registernamen,
  des Filters, des Panorama- oder sonstiger DSP-Parameter.

## Verbindliche Abnahme und Grenzen

Die Änderung ist **bewusst anders als die V11-SoundFont-Neutralstellung**.
Vor einem Merge/Release sind eine explizite V11-Projektmigrationsstrategie
und Legacy-Recall-/Save-/Automationtests erforderlich; alte Projekte
dürfen nicht stillschweigend anders klingen. P190 ist daher zunächst
nur ein **nicht freigegebener Fix-Kandidat**.

Alle produktiven Windows-VST3-Builds müssen die gesamte CTest-Suite
inklusive 125A_p190_fx_zero_dry, den VST3-Validator, 3 EditorHost-
Smokes und das universelle Test Lab bestehen. Echte PCM-Behauptungen
müssen durch binäre L/R-Werte sowie send-register-oracle gedeckt sein.
Ein Test mit Nutzer-ROM, -SF2 und DAW bleibt NOT_RUN, wenn entsprechende
Dateien nicht vorliegen. P184/P189-ASIO-NO-GO bleibt bestehen.

**Keine VST3-Verkaufsfreigabe und kein FULL AUDIT aufgrund eines grünen
Entwicklungsbuilds.**
