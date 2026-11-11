# P228/P229: unabhängige Original-Creative-/SF2-Belege

[Technischer Bericht und offene Fehler](../../docs/P229-INDEPENDENT-SF2-CLIPPING-AUDIT.md).
[Maschinenlesbare Zusammenfassung](independent-sf2-summary.json).

Diese Git-Ablage enthält ausschließlich aggregierte numerische Ergebnisse, Hashes, Testlogs
und archivierte Sitzungsadapter zu **bestehenden** P228/P229/P48/P89/P234-Prüfern.
Sie legt keine weitere Testinfrastruktur an. Keine Aufnahme wird als physische
AWE-Hardware ausgegeben. Es befinden sich keine ROMs, SF2s, Samples,
Creative-/Windows-Dateien, Diskimages oder PCM-Aufnahmen in dieser Ablage.
Die vollständigen privaten Einzelfallergebnisse bleiben im getrennten
Besitzerpaket `P229_PRIVATE_NUMERIC_EVIDENCE_20261111.zip` außerhalb von Git;
auch dieses enthält keine Originalmedien oder PCM. Das
[Datei-/SHA-256-Manifest](PRIVATE-EVIDENCE-SHA256.json) authentifiziert sämtliche
Dateien dieses privaten Pakets. Es werden keine privaten 3.082-/234er-
Einzelfallmatrizen oder vollständigen Besitzerbank-Hüllkurven veröffentlicht.

## Vollständige Belege im privaten Besitzerpaket lesen

- `p228-bank-0.csv` bis `-3.csv`: sämtliche 3.082 neu ausgeführten nativen Fälle.
- `p229-bank-0.csv` bis `-3.csv`: 117 Clipping-Fälle und ihre 117 identischen V48-Kontrollen, einschließlich echter Signed32-Überbereichswerte.
- `source-media-hashes.json`: Zuordnung Bankindex, Originaldatei und SHA-256.
- `original-bank-N-p67-verification.json`: echte Win95-/Creative-Endpunkt-/Zustellnachweise nach Schließen des jeweiligen Gastes.
- `original-bank-N-upload-analysis.json`: vollständige Original-SMLD-RAM-Schreibabdeckung und widerlegte Roh-PCM-/vereinfachte Präemphase-Modelle; keine Samplewörter publiziert.
- `attenuation-layer-register-analysis.json`: unabhängig aus Original-SF2-Metadaten zugeordnete Sampleadressen, 790 Layerpaare, IFATN-Lowbytes und direkte Ganzzahlvorhersagen. Originale Stimmenummern werden nicht als Layeridentität missbraucht. In Git steht davon ausschließlich das Aggregat.
- `sample-accurate-same-tap-comparison.json`: endgültige 234 Vergleiche vor FX/EQ, jeweils genau 88.200 Frames, tatsächliche Registerkanten, L/R-RMS/Peak, fünf Spektralbänder und 10-ms-Hüllkurven, ohne Normalisierung. In Git stehen davon ausschließlich Aggregate und Methodik.
- `same-tap-effect-stage-witness.json`: warum originales CC91/93=0 keinen erlaubten Post-FX-Dryvergleich ergibt; native GUI-0-Rückwege tatsächlich null.
- `fresh-layer-count-witness.json`: vier zusätzliche echte Original-Noten in einem frisch gebooteten Gast; 6 statt 8 aktive Layer.
- `p229-observed-upload-bank-N.csv`: diagnostisch ausschließlich gemessenen Original-Sample-RAM eingesetzt; 4 native Restfälle.
- `p229-observed-upload-ifatn-bank-N.csv`: zusätzlich ausschließlich gemessene IFATN-Lowbytes eingesetzt; 2 native Restfälle. Kein Produktpatch.
- `p229-fast-only-six.csv` / `p229-upload-plus-fast-six.csv`: verworfene Schnellattack-Gegenprobe, keine behauptete Clipping-Korrektur.
- `native-p234-observer-bitexact.json`: alle 234 PCM16- und Raw32-Dateien mit/ohne lesende Beobachter bytegleich.
- `dc-overflow-negative-control.json`, P83-Testlog und Header-/Sustain-Testlogs: konkrete Diagnose-/Testkorrekturen.
- `native-fixed-regression-ctest.log`: 41/41 Linux-CTests gegen Produktkern 8d2f41d mit sechs QA-Dateien aus ca68572, ohne DSP-Beobachter.
- `windows-fixed-ctest.log`: [Windows-2022 #43028856058](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/43028856058), 49/49, vollständiger exakter QA-Commit ca68572.

## Wiederholung mit Originalmedien

Die vier Originaldateien und der vollständige P228-Eingabeplan verbleiben privat.
Die gepostete CSV mit 3.082 Zeilen ist dieser **Eingabeplan**, keine alte
Clipping-Ergebnisdatei. Vor Wiederholung Größen und SHA-256 gegen
`source-media-hashes.json` sowie die gemeinsame Original-ROM prüfen.

Die ausgeführten nativen Aufrufe verwenden den ursprünglichen Prüfer:

```text
p228_batch_dry_native awe32.raw ORIGINALBANK.sf2 P228-Trockensound-Testmatrix.csv OUTPUT.csv 0
p229_dry_preclip_native awe32.raw ORIGINALBANK.sf2 REPRODUZIERTE-234-PLANZEILEN.csv OUTPUT.csv 0 --private-captures PRIVATE-DIRECTORY
```

Der erste Lauf erzeugt die 117er-Liste. Je V112-Fall wird ausschließlich die
gleiche Bank/Programm/Note mit V48 aus dem Originalplan als Kontrolle gewählt.
Alle CSV-Spalten und die ursprünglichen Dateinamen bleiben erhalten.
Den Diagnosequelltext gegen die Header und statische Bibliothek des **exakten
Produktkerns 8d2f41d** bauen, nicht versehentlich gegen den älteren Produktkern
des reinen Berichtsbranches. Die ursprünglichen P228-/P229-Toolquellen waren an
beiden Ausgangsständen identisch. Die DC-/Mitschnittkorrektur liegt in 3cab2d7.

Die Originalreferenz benutzt unverändert das vorhandene private Engineering-
[P38/P40/P48-Gastverfahren](https://github.com/challanger2000/125A-Engineering/blob/807d60b10680bfd6e49cd2af80672209aee990c5/.github/workflows/p230-original-creative-gm-pilot.yml)
für identisches Image, Originaltreiber, AWE-Control-Panel und CRT-freien P63-
Agenten. Es wird daraus **kein GM-/Cutoff-Test** ausgeführt. Der Sitzungsadapter
`reproduction/replay_in_existing_p48.py` hängt lediglich die identischen P229-
MIDI-Fälle an den schon laufenden P64-Gast an. Er benutzt die existierenden
P89-/P234-Parser und -Abgriffe. Die archivierten `/workspace`-/`/tmp`-Pfade sind
die tatsächlich verwendeten Sitzungsorte; vor Wiederholung an den privaten
Arbeitsort anpassen. Das Skript ist kein portables Installationspaket.

Pro Bank werden die vorhandenen P48-Argumente `--p64-bridge`,
`--universal-sf2`, `--universal-sf2-bank 0`, `--universal-programs P1,P2`,
`--universal-note N` und `--sound-card sbawe64_gold` verwendet.
`P229_BANK_INDEX` ordnet 0–3 zu; `EMU8K_P233_STAGE`, `EMU8K_P234_DRY_PCM` und
`EMU8K_P234_GATE` aktivieren ausschließlich die bestehenden privaten Lesetaps.
Für die frische Gegenprobe gelten `P229_CASE_IDS=15,16,51,52` und
`P229_REPLAY_SUFFIX=-fresh-layer-witness` bei Bankindex 3. P67 anschließend
auf dem geschlossenen Gast auswerten; bloße vorhandene Treiberdateien sind
keine Originalreferenz.

Die `reproduction/*.patch`-Dateien sind archivierte **alternative** Eingriffe
allein in das vorhandene P229-Diagnoseprogramm. Niemals gemeinsam oder als
Produkt-Enginepatch übernehmen. `p229-observer-only.patch` protokolliert
P234-Bytebereiche; die bestehenden P233/P234-Quellbeobachter laufen nur auf
einer lokalen, wegwerfbaren Quellkopie. Die anderen Patches setzen wahlweise
das tatsächlich beobachtete private RAM-Abbild und gemessene IFATN-Lowbytes
ein oder führen die ausdrücklich verworfene Attack-Kontrolle aus. Die
Produktbibliothek dieser Eingriffe bleibt unverändert. Für die IFATN-Probe
wird die ursprüngliche Filterhälfte des Registers unverändert übernommen.

Private PCM/RAM/I/O-Dateien verbleiben außerhalb dieser Ablage. Hashes
ermöglichen den Abgleich mit den vorliegenden privaten Dateien; sie ersetzen
keine fehlende Originalaufnahme. Die beigefügten numerischen Zusammenfassungen
erklären ausdrücklich sämtliche noch offenen Bereiche. **Klangfreigabe BLOCKED.**
