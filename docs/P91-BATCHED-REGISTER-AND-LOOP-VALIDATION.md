# P91 – gebündelter Win95/SF2 Note-off-Registerabgleich

Basis: tatsächlicher P89-Vergleich gegen Creative unter Windows 95 (Programm 0, Note 48, zwei Stimmen). Vier P90-Konvertierungen sind separat bereits korrigiert.

## Zwei generische Korrekturen, ein gemeinsamer Testlauf

1. **SF2 SampleModes 1 vs. 3:** Modus 1 ist eine kontinuierliche Schleife und bleibt beim Note-off unverändert; Modus 3 gibt beim Loslassen den Loop für das Sample-Ende frei. Bisher öffnete die Win95-Schiene beide SF2-Modi. Für SF1 und DOS bleibt das bisherige Verhalten bestehen. P89: zusätzliche PSST/CSL-Rewrites der nativen Stimme, die der Originaltreiber bei diesem Sound nicht hatte. Dies ist eine aus SF2-Semantik abgeleitete Korrektur, deren Wirkung im aktuellen Originalvergleich noch gegenzuprüfen ist.
2. **Doppelte DCYSUSV-Silence-Schreiboperation:** Die Win95-Stimmenallokation schreibt bereits 0x00FF; der Note-on-Pfad schrieb denselben Wert ein zweites Mal. P89 maß genau diesen zusätzlichen Eintrag bei 125A. Die einmalige Stummschaltung bleibt erhalten.

Das C++-Registertestprogramm prüft SF2-Modi 0/1/3. Die native 86Box-Synth-Integration prüft den Unterschied an **generierten, rechtlich unproblematischen SF2-Testwellen** mit 64 Wörtern Sample-Auslauf nach dem Loop. Die Python-Trace-Diagnose unterscheidet nun Fehlwerte beim **ersten Registerschreiben** von weiteren späteren Umschreibungen; der P89/P90-Windows-95-Originaltrace bleibt ausschlaggebend.

**Batch:** ein Commit stößt einen nativen Linux-Integrations-Build und einen Windows-x64-VST3-/CTests-/Python-Regressionslauf an. Keine Einzel-Builds je Registerfix.

**Noch NICHT korrigiert:** LFO1-/LFO2-Geschwindigkeiten, Attack um 1, Pitch um 1, ungeklärte Spektralabweichungen. Dafür erst Originalmessungen über mehrere Werte/Patches auswerten, nicht die erste Bass-Vorgabe hart codieren. Keine Behauptung einer 1:1-Hardwaretreue.
