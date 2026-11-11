# P104 – Ausgeführter Integrations-/QA-Folgeauftrag

Stand: 11.11.2026. Verbindliche Projektleitung: [#103](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/103) und [#104](https://github.com/challanger2000/125A-AWE-Synthesizer/issues/104), einschließlich der Folgeanweisung vom 11.11., 01:16 UTC. Keine neuen Branches, Merges oder Löschungen; keine Änderung der produktiven EMU8000-Klangerzeugung oder ASIO-Grenzwerte.

## Bericht und vollständiger Bestand

Der abgeschlossene Bestandsaudit wird unverändert als datierter Snapshot veröffentlicht. Lokale Workspace-Links sind für andere Chats nicht ausreichend; die Dateien liegen jetzt unter `docs/evidence/REPOSITORY-AUDIT-20261111/`:

- [Vollständiger INTEGRATIONSBERICHT.md](evidence/REPOSITORY-AUDIT-20261111/INTEGRATIONSBERICHT.md).
- [142 Branches – CSV](evidence/REPOSITORY-AUDIT-20261111/BRANCH-INVENTAR-142.csv) und [JSON mit Commitlisten, CI-Fundstellen und Abhängigkeiten](evidence/REPOSITORY-AUDIT-20261111/BRANCH-INVENTAR-142.json).
- [89 PRs – CSV](evidence/REPOSITORY-AUDIT-20261111/PR-INVENTAR-89.csv), [JSON](evidence/REPOSITORY-AUDIT-20261111/PR-INVENTAR-89.json) und [Disposition der 54 offenen PRs](evidence/REPOSITORY-AUDIT-20261111/OFFENE-PRS-54.md).
- [PR-Abhängigkeitsgraph – Mermaid](evidence/REPOSITORY-AUDIT-20261111/PR-ABHAENGIGKEITEN-54.mmd) und [JSON](evidence/REPOSITORY-AUDIT-20261111/PR-ABHAENGIGKEITEN-54.json).
- [75 Archiv-/Löschvorschläge mit exakten SHAs](evidence/REPOSITORY-AUDIT-20261111/ARCHIV-LOESCHVORSCHLAEGE-75.md), [CSV](evidence/REPOSITORY-AUDIT-20261111/ARCHIV-LOESCHVORSCHLAEGE-75.csv), [43 vorhandene Tags](evidence/REPOSITORY-AUDIT-20261111/BESTEHENDE-TAGS-43.json).
- [Auditmanifest und Geltungsgrenzen](evidence/REPOSITORY-AUDIT-20261111/AUDIT-MANIFEST.json), [bestehende CI-Run-SHAs](evidence/REPOSITORY-AUDIT-20261111/CI-NACHWEISE.json), [ursprüngliches Auditpaket als ZIP](evidence/REPOSITORY-AUDIT-20261111/AWE-Repository-Audit-20261111.zip).

Snapshot: **A 3 / B 64 / C 44 / D 31**; 31 offene PR-Heads sind bereits Vorfahren des Kandidaten, alle 35 tatsächlichen Merge-/Squash-Ergebnisse geschlossener PRs sind enthalten. D ist nur ein bedingter Entfernungsvorschlag nach Archiv-/Evidenzprüfung und Auftraggeberfreigabe. Nichts wurde bereinigt.

**Vorläufiger Produkt-/Integrationsausgangspunkt bleibt** `fix/creative-volume-sustain-layer-parity` / `2bd6d2d299a53f9af1e741e625d22207e08c8909`. Dieser Folgecommit veröffentlicht ausschließlich Dokumentation und Prüfbelege. Der produktive src-/Test-/CMake-Stand des AWE-Repositories bleibt exakt gleich. Ein vollständig integrierter und vollständig geprüfter Gesamtstand wird nicht behauptet.

Der P232-Zweig wurde weiterentwickelt: ursprünglicher Snapshot-Head `7b7553fb9562c8b65cdd1541e7066823fba10954`, beim Folgeabruf `1899b3389b263603f012e7f3ee35eb5b75a2ad36`. Diese laufende Entwicklerarbeit wird hier nicht abgenommen oder verändert. [Abrufkontext und Folge-Heads](evidence/REPOSITORY-AUDIT-20261111/followup-104/PUBLICATION-CONTEXT.json). Die neue Architektur-/Orakeltrennung aus #103 bleibt beim bestehenden P232-Ursachenpfad; hier wird kein Renderer ersetzt.

## 1. Stereo-Prüflücke behoben

**Test-Lab-Korrektur:** [`0832e1573a9ba83d3fdae43a63917554a0440aa8`](https://github.com/challanger2000/125A-Plugin-Test-Lab/commit/0832e1573a9ba83d3fdae43a63917554a0440aa8), ausschließlich auf dem bestehenden Branch `qa/p220-awe-sf2-77-sound-gate`.

P220 erhält echte L/R-PCM-Streams, kanalweise RMS/Peak/Envelope/Spektrum, gemeinsame feine Zeitausrichtung mit vorhandenem P90-PCM-Vergleicher und L/R-/Mid-Side-Strukturprüfungen. Stereoenergie ersetzt die Mono-Auslöschung bei der Signalpräsenzprüfung. P89 blockiert alte Mono-Reports und fehlende fallweise Stereo-/PCM-Belege.

Vergleichsversion **p220-stereo-v2**, Testversion **p220-stereo-regression-v2**. Die absolute 1-dB-Pegelgrenze bleibt trotz P90-Gain-Schätzung verpflichtend; Original-WAVs werden nicht normalisiert oder repariert. [Alle Grenzen und abgeschlossenen CI-Nachweise im Test-Lab-Vertrag](https://github.com/challanger2000/125A-Plugin-Test-Lab/blob/6cc9579714c56ee14afa8d5b1612aeeec2f4fac1/docs/P220-AWE-SF2-77-ORIGINAL-CREATIVE-SONIC-GATE.md). Die früheren 154 Positiv-WAVs waren Dual-Mono und konnten einen Kanaltausch grundsätzlich nicht nachweisen.

**Lokal ausgeführter RED/GREEN-Nachweis mit identischem Testquellhash und identischer P90-Abhängigkeit:**

| Kontrolle mit tatsächlichen synthetischen PCM16-Stereo-WAVs | Alt | Korrektur |
|---|---|---|
| Asymmetrisch mit unabhängigem 1-LSB-Unterschied | PASS | PASS |
| Tatsächlich identisches Dual-Mono nach Tausch | PASS | PASS |
| Passende Antiphase | fälschlich FAIL | PASS |
| Passendes Hard-Left / ruhiger rechter Referenzkanal | PASS | PASS |
| Gemeinsamer +0,5-dB-Gain bzw. 211-Frame-Aufnahmeversatz | jeweils PASS | jeweils PASS |
| Asymmetrischer L/R-Tausch | fälschlich PASS | FAIL |
| Nur linker bzw. rechter Kanal stumm | jeweils FAIL | jeweils FAIL |
| Rechter Kanal −3 dB | fälschlich PASS | FAIL |
| Rechte bzw. beide Polaritäten invertiert | jeweils fälschlich PASS | jeweils FAIL |
| Ausschließlich rechts 128 Frames Verzögerung | fälschlich PASS | FAIL |

**7/13 → 13/13 erfüllte Erwartungen.** Fehlerhafte Signale besitzen gültige WAV-Header und frisch passende SHA-Receipts; die Ablehnung ist akustisch begründet. [Vorher-JSON](evidence/REPOSITORY-AUDIT-20261111/followup-104/stereo-before.json), [Nachher-JSON](evidence/REPOSITORY-AUDIT-20261111/followup-104/stereo-after.json), [RED-Log](evidence/REPOSITORY-AUDIT-20261111/followup-104/stereo-before.log), [GREEN-Log](evidence/REPOSITORY-AUDIT-20261111/followup-104/stereo-after.log).

Die vollständige bestehende P220-Suite besteht lokal zusätzlich mit **154/154 synthetischen Vergleichen und 10/10 erkannten bisherigen Mutationen**. [Lokales P220-Log](evidence/REPOSITORY-AUDIT-20261111/followup-104/p220-full-linux.log). Weitere lokale Regressionen: P220/P89-Releaseintegration 5/5, allgemeiner P89-Reporter 4/4, unveränderte P90-Capture-Prüfung 10/10.

**Windows und Ubuntu tatsächlich abgeschlossen:** [Run #42939861242 SUCCESS](https://github.com/challanger2000/125A-Plugin-Test-Lab/actions/runs/42939861242), exakter QA-Quellcommit `0832e1573a9ba83d3fdae43a63917554a0440aa8`. [Windows-2022 #130258823938 SUCCESS](https://github.com/challanger2000/125A-Plugin-Test-Lab/actions/runs/42939861242/job/130258823938), [Ubuntu-24.04 #130258824439 SUCCESS](https://github.com/challanger2000/125A-Plugin-Test-Lab/actions/runs/42939861242/job/130258824439). Beide führen die 13 Stereoerwartungen, 154 synthetischen Vergleiche, zehn bisherigen Mutationen und 19 P89/P90-Regressionen aus. Ohne originale Aufnahmen bleibt das separate Klang-Gate **77 BLOCKED / 0 PASS**.

[Maschinenlesbarer CI-Nachweis mit beiden Artefakt-IDs und veröffentlichten Archivdigests](evidence/REPOSITORY-AUDIT-20261111/followup-104/P220-CI-EVIDENCE.json). Windows-Artefakt 13820017799, Ubuntu-Artefakt 13821075153. Öffentliche Jobstatus und Digests wurden geprüft; ZIP-Bytes/Windows-Rohlogs verlangen GitHub-Login und wurden nicht als unabhängig heruntergeladen ausgegeben. Die lokalen [19 Kompatibilitätsregressionen](evidence/REPOSITORY-AUDIT-20261111/followup-104/compatibility-linux.log) und [Umgebungsdaten](evidence/REPOSITORY-AUDIT-20261111/followup-104/compatibility-linux.json) liegen zusätzlich vor.

Dies ist ein Vergleicherskript-Test, kein nativer Plugin-Neubuild, keine Original-Creative-Klangabnahme und keine Releasefreigabe. Der spätere Test-Lab-Dokumentationscommit `6cc9579714c56ee14afa8d5b1612aeeec2f4fac1` enthält ausschließlich die abgeschlossenen Nachweise; die getesteten Skripte und der Workflow sind unverändert zum obigen Quellcommit.

## 2. P196 und P198: Integrationsfähigkeit tatsächlich geprüft

| | P196 | P198 |
|---|---|---|
| Quelle / Commit | [`f308b71a4765e2402856e7be24105420542e37a1`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/f308b71a4765e2402856e7be24105420542e37a1) | [`2f986648d0507ba97c804b483ce00021a2f656fe`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/2f986648d0507ba97c804b483ce00021a2f656fe) |
| Herkunft | `fix/p190-zero-fx-dry` | derselbe Seitenzweig, nach P196 |
| Produkt-/Testdateien | `src/engine/SoundFont.cpp`, `tests/p90_sf2_driver_registers.cpp` | dieselben zwei Dateien |
| Dokument im Originalcommit | `docs/P196-SF2-ZERO-SCALE-HARDWARE-FIX.md` | `docs/P198-SF2-ATTENUATION-HARDWARE-CALIBRATION.md` |
| Fehlendes Delta in Kandidat 2bd6d2d | explizites SF2/Win95 scaleTuning=0 erhält feste Tonhöhe | SF2/Win95 InitialAttenuation 0.40 → 0.50 |
| Aktuelle Kandidatenquelle | alter tonhöhenabhängiger Nullpfad | weiterhin Faktor 0.40 |
| Original-Windows-Nachweis | [#42588685864 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42588685864) | [#42593301776 SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42593301776) |
| Dort dokumentierter Umfang | 67 CTests, 537 Modulvalidator, 99 GUI, drei Smokes, Test Lab, 0/14.400 LAB_ONLY | derselbe Vollregressionsumfang für diesen separaten Source-SHA |
| Begrenzung | keine Abnahme des späteren gemeinsamen Integrationsstands | CT4390-Analogkalibrierung, keine bewiesene exakte Win95-VXD-Formel; primäres #103-Orakel getrennt |

**Durchgeführt:** Die auf die beiden Produkt-/Testdateien begrenzten Originalpatches wurden in einem isolierten temporären Git-Index auf `2bd6d2d` mit `git apply --cached --check` geprüft. P196 zuerst: Exit 0. P198 danach: Exit 0. Gegenkontrolle P198 zuerst und P196 danach: ebenfalls beide Exit 0. Beide Reihenfolgen ergeben exakt denselben Prüfbaum `a9325dcba5f79849827f1a795fe590479b7fe271`. Das ist ein lokales Baumobjekt, kein Mergecommit oder freigegebener Source-Commit.

Die gesamte simulierte Differenz betrifft ausschließlich SoundFont.cpp und den P90-Test. Die getrennten Mod-/Vol-Sustain-Provenance-Pfade bleiben erhalten. Synth.cpp, snd_emu8k.c, VST3-Factory, GUI und State bleiben auch im hypothetischen Prüfbaum unverändert. Im tatsächlichen Produkt-Working-Tree wurde **kein Patch angewendet**.

[Maschinenlesbares Prüfprotokoll](evidence/REPOSITORY-AUDIT-20261111/followup-104/P196-P198-INTEGRATIONSPRUEFUNG.json), [P196-Originaldelta](evidence/REPOSITORY-AUDIT-20261111/followup-104/P196.patch), [P198-Originaldelta](evidence/REPOSITORY-AUDIT-20261111/followup-104/P198.patch), [hypothetische kombinierte Differenz](evidence/REPOSITORY-AUDIT-20261111/followup-104/P198-combined-source.diff).

**Urteil:** Textuelle/dateibezogene Integrationsfähigkeit nachgewiesen. Keine belegte textuelle Abhängigkeit zwischen den Deltas; P196 → P198 bleibt die nachvollziehbare historische Integrationsfolge. Klangliche Verträglichkeit der Kombination, gemeinsame Windows-Gesamtregression und originale Win95-SF2-Abnahme sind **NOT RUN**. Nach dem P232-Gate zuerst P196 separat übernehmen und prüfen; P198 erst nach ausdrücklicher Referenz-/Verhaltensentscheidung der Projektleitung, anschließend gemeinsame Regression. Kein stiller Koeffizientenwechsel und keine zusätzliche globale ROM-Gain-Korrektur.

**P223 bleibt ausgeschlossen:** `3ae1b26322adf36e841a7e926a97352021139944` ist eine hörbare Änderung der FX-Send-Kennlinie. P190 **0% = dry** bleibt verbindlich. Ebenso kein Chorus-Rundungsmerge und keine Übernahme von Forschungsrenderer-Varianten.

## 3. Abnahme- und Veröffentlichungsgrenzen

Die Dokumente machen die vollständige Audit-/Integrationsgrundlage auf GitHub prüfbar. Das Inventar bleibt ein datierter Snapshot; neue P232-Commits sind daraus nicht automatisch abgenommen. P232 bleibt auf seinem vorhandenen Branch beim Entwickler.

Der direkte GitHub-API-Abruf für #104 wurde von der Cloudverbindung mit **Forbidden** zurückgewiesen; ein API-Kommentar wurde nicht als erfolgreich ausgegeben. Veröffentlichung über den bestehenden Git-Branch und einen Refs-#104-Commit mit Dateilinks. Kein neuer Branch oder neues Testsystem als Ausweichlösung.

**Keine neue Original-Creative-/397-ROM-/Vier-SF2-/DAW-/ASIO-Abnahme ausgeführt. Kein FULL AUDIT und kein Release-PASS.** P184 wurde nicht wiederholt; ASIO-Grenzwerte, Sperren und produktive Klangerzeugung sind unverändert.
