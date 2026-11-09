# P189 – zuerst vorhandene ETW-Rohdaten erneut auswerten, OHNE ASIO-Messung

## Ausgangsbefund aus dem Yamaha-Steinberg-ASIO-Zielrechner

Die letzten beiden realen Windows-ASIO-Referenzmessungen ergaben
**1.000/1.000 korrekt verarbeitete Callbackblöcke**, null DSP-Fehler,
null Callback-Ausführungszeitüberschreitungen und null XRUN-Meldungen.
Allerdings gibt es jeweils **eine** Startabstandsverletzung.
Die vorherige ETW-Decodierung lieferte bei einem Lauf 43.425 Fehler
auf 125.671 ETW-Ereignisse, beim anderen 72.039 auf 189.704
Ereignisse und jeweils **0 verwertbar zugeordnete Kontextwechsel**.
Dies beweist nicht, dass das Betriebssystem keine Kontextwechsel hatte.
Die ETW-Aufzeichnung funktionierte, der Parser konnte die Ursache
der Startlücke aber noch nicht verifizieren.

## Empfehlung: P189-REPLAY.bat zuerst, kein neuer Audiotest

1. Das **tatsächlich auf Windows gebaute und geprüfte P189-Artefakt**
   vollständig in einen beschreibbaren Ordner entpacken.
2. `P189-REPLAY.bat` starten – **ohne Administratorrechte**.
3. Den vorhandenen `P185-LOCAL-...`-Ordner des jüngsten
   P188-Tests auswählen (alternativ `RAW-LOCAL-ONLY`).
4. **Nur `P189-REPLAY-.../P189-RESULT.json` hochladen.**
   Die ETL-Dateien (`kernel.etl`, `providers.etl`) verbleiben
   ausschließlich lokal. Die ursprünglichen Dateien werden nicht
   überschrieben oder gelöscht.

P189 liest die bereits gespeicherten ETL-Dateien mit dem neu
instrumentierten universellen 125A-Test-Lab-Decoder neu ein. Es
startet keine Windows-ETW-Session, keinen ASIO-Prozess,
keine DAW, kein Audiogerät und gibt keinen Ton aus.
Die kompakte JSON benennt die gezählten Kern- und Thread-Ereignisse
sowie bis zu 32 konkrete Fehlerkategorien mit
ETW-Ereignistyp, TDH-Feldname und Windows-Statuscode.

Das Replay-Ergebnis ist eine **Diagnose, kein Hardware- oder
AWE-Release-PASS**. Bei nicht vorhandenen ETL-Dateien wird
der echte Lauf nicht fingiert. Insbesondere
`physical_asio=NOT_VERIFIED_OFFLINE` bleibt verbindlich.

## Nur falls die Rohdaten fehlen

Die zweite vorhandene `P189-ETW-ASIO.bat` übernimmt die
erfolgreiche P188-Rechte-/ETW-Vorprüfung und ermöglicht *nach
ausdrücklichem START* genau eine neue reale Referenzmessung
mit 44.100 Hz, 512 Samples und 1.000 angeforderten
Callbacks. Dafür DAW vorher schließen und Lautstärke reduzieren.
Bei ETW-Preflight-Fehler wird kein Audio gestartet;
dann nur `P188-PREFLIGHT.json` bereitstellen.
Bei neuer echter Audiomessung nur
`P185-LOCAL-.../P185-ACCEPTANCE.json` bereitstellen.
Keine ROM/SF2, kein Python, keine VM.

## Qualitätssicherung

Der veränderte universelle ETW-Decoder und die Offline-Nachdecodierung
wurden als Windows-x64-Software samt echtem ETW-Selftest und
unabhängigen Negativkontrollen gebaut und geprüft.
Für die Integration ist zusätzlich erforderlich:
- Windows-Build aller nativen Testtools mit festgepinnten
  Test-Lab- und Audio-SDK-Quellen;
- unveränderte AWE- und ASIO-Audiolaufzeit samt Regression;
- präzise ETW-Diagnose mit 36 P185- und 42 P186-Gegenproben;
- **echte Nachdecodierung der im Windows-Selftest erzeugten ETL-Dateien**
  und Vergleich der Ereigniszähler;
- Paket-Hashprüfung, BAT-Abbruchkontrollen und absichtliche
  Manipulationen, die zuverlässig abgewiesen werden;
- Hochladen des originalen ZIP-Artefakts, erneutes Herunterladen
  von GitHub und `P189-REPLAY.bat -CheckOnly` am
  tatsächlich heruntergeladenen Paket.

Ohne nachweislich grünen Integrationslauf **keine Benutzerabnahme**.
Der AWE-Klangkern, P184-Nachweise, der vollständige
2×Buffer-Startabstandsgrenzwert und die Release-Sperre
bleiben unverändert. **Ursache INCONCLUSIVE, AWE-Release NO-GO,
kein FULL AUDIT.**

Universalquelle:
`challanger2000/125A-Plugin-Test-Lab`,
`fix/p189-etw-schema-observability`,
Commit `bf6f8fc69e88624762861dbb9a20384cfe3f09a4`.
