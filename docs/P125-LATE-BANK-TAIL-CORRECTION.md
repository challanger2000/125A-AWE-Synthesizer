# P125 — Late-bank ordering and VST3 tail correction (candidate, NO-GO)

**Stand 2026-11-05. Kein GUI-GO und kein Release-GO.**

## Anlass: unabhängiger P124-Nachaudit war FAIL

Der unabhängige Codex-Nachaudit zu **P124-Code `2f0c4d225f41f51c1b37d3c04986845024c0f80f`** meldete:

- **HOCH / FAIL:** Nach komplettem Recall Bank 0 kann ein bereits laufender Audioblock Bank 5 über die VST3-Parameterqueue oder MIDI CC0 erfolgreich übernehmen; ein **verzögerter Recall-Befehl** setzt im folgenden Block trotzdem die Bank zurück auf 0. Bei VST3 ist sogar `getState(): 5 -> 0` ohne neue Hostbankänderung reproduzierbar. Der P124-Test hatte nur einen nach Beginn des Recalls angenommenen UI-Browser-Nachrichtenauftrag, nicht den **umgekehrten, bereits gestarteten Audioblock** mit späteren Parameter-/CC-Eingängen geprüft.
- **PASS:** `setProcessing(true/false)`, strict Lifecycle und Restart/Tail-Erhalt über Processing-Übergänge.
- **Zusatzbefund:** `getTailSamples()` meldete 0 trotz ca. 0,9 s realer ausklingender Ausgabe.
- **Offen:** Unter hoher Last Deadline-Überschreitungen und eine Save-Abweisung; die P123-Zustandsregressionen bestanden in den gemeldeten Gegenproben erneut.

Die kompletten unabhängigen P124-Rohdaten befanden sich in der externen Codex-Umgebung (`/tmp/P124-Nachaudit-2f0c4d2.md` und Archiv); sie waren **nicht** in dieser GitHub-Sitzung verfügbar. Obige Aussagen beruhen auf dem übermittelten Audit-Ergebnis und ergänzender Codeeinsicht; sie sind keine behauptete eigene Reproduktion dieses externen Aufbaus.

## Neue Korrektur — geprüft, aber noch nicht unabhängig abgenommen

- **Produktionscode:** [`af6a8fdd02ab2c2fe7d3ea50d47892d4e2967fac`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/af6a8fdd02ab2c2fe7d3ea50d47892d4e2967fac)
- **Produktionscode + neue Regression:** [`805a2ef1d49133aae022256161c275240ac80fed`](https://github.com/challanger2000/125A-AWE-Synthesizer/commit/805a2ef1d49133aae022256161c275240ac80fed)
- **Windows GitHub Actions:** [Run #42069200394 — SUCCESS](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42069200394). Echter Windows-x64-VST3-Build, enthaltene native/VST3-Regressionen, Steinberg-Prüfphase, Metadatenprüfung und EditorHost/Paketierungsworkflow erfolgreich.
- **Keine Änderungen** an ROM-Pflicht, 28-MiB-Speicherlimit, FM-Modus, DSP-Algorithmus oder GUI-Funktionsumfang.

### Implementiert

1. `Factory.cpp`: Wenn der laufende Audio-Callback **nach** einem Recall noch einen neuen Bank-Parameterwert oder MIDI-CC0/CC32 annimmt, wird der schon vorhandene verzögerte Recall-Bankauftrag **als überholt markiert**. Später angenommene Browser-Nachrichten sollen weiterhin als neue Aufträge gelten; das Audio-Callback wartet nicht auf Control-Threads.
2. Browserbank-Invalidierung wird beim Eintreffen eines **späten MIDI-Bankereignisses** noch einmal mit dem aktuellen Recall-Epoch synchronisiert, nicht ausschließlich am Beginn des Audioblocks. Damit soll eine neuere CC0/CC32-Auswahl im nächsten Block erhalten bleiben.
3. `getTailSamples()` liefert `kInfiniteTail` statt 0. Die Grenze ist bewusst konservativ: beliebige Sample-/SF2-Hüllkurven und Effektausklänge haben keine für alle User-Bänke garantierte kurze Dauer. Ziel-DAW-Verhalten und die praktische Suspend-Last müssen getestet werden.

### Neue VST3-Regression

In `tests/p122_vst3_bank_host.cpp` blockiert eine echte Host-`IParameterChanges::getParameterCount()`-Implementierung **nach** Beginn von `process(128)`. Während dieser Pause führt der Control-Thread `setState(bank=0)` vollständig aus. Anschließend übernimmt derselbe noch laufende Callback bei Sample 64 **kBankID=5**. `getState` muss vor **und nach** einem weiteren leeren Audioblock Bank 5 ergeben; ein später absichtlicher Parameterwechsel nach Bank 0 muss weiterhin funktionieren. Auch der `kInfiniteTail`-Interfacevertrag wird geprüft.

Dieser Windows-Test ist erfolgreich, aber er ist kein vollständiger Ersatz für den unabhängigen P124-Adapter mit **tatsächlich geladenem synthetischem ROM/SF2**, echten CC0-/CC32-Soundbankwirkungen, kontrolliertem Scheduling und hohen Lastbedingungen.

## Unabhängiger Prüfauftrag für den exakten Kandidaten 805a2ef1 (READ ONLY)

1. **Die ursprüngliche P124-FAIL-Reproduktion unverändert wiederholen:** bereits gestarteter und im Parametergetter unterbrochener 1024-Frame-Callback, Recall Bank 0 komplett, später Bank 5 bei Frame 512, CC7=32, Programm 9; getrennt **kBankID (1002)** und **MIDI CC0**, jeweils gespeicherter Zustand **vor/nach dem Folgeblock** und tatsächlich gespielte Bank. Zusätzlich CC32 und andere Kanäle; serielle Positivkontrollen. Ein synthetisches, erlaubtes ROM/SF2 genügt.
2. **Neue Race-Grenzen prüfen:** UI-Bank-Nachricht während/nach einem späten CC0, verschachtelte schnell folgende Browser- und Recall-Aufträge, Callback-Epochenwechsel direkt zwischen CC0-Annahme und Acknowledgement, Gate-Kollision ohne stillschweigend verlorene Bankbefehle. Neue Nachrichten dürfen nicht irrtümlich durch das Acknowledgement übersprungen werden.
3. **Tail:** ein nachweislich ca. 0,9 s klingendes Instrument in striktem Host, tatsächlicher `getTailSamples`-Rückgabewert und Fortsetzung der Verarbeitung bis zur Stille; bei `kInfiniteTail` auch Idle-/Suspend-Verhalten beobachten.
4. **Regression:** P123 30.000 multi-writer state roundtrips, 500/500 klingende Saves, Processing-Lifecycle, 44,1/48/96-kHz-Pan, 16-MIDI-Kanäle, Bankbrowserfehler-Retry.
5. **Lastbefunde separat messen:** Deadline bei 30 Stimmen und dichten Pitchpunkten; Save-Abweisung unter hoher Konkurrenz. Werte nicht verschweigen und nicht dem Bankfix als behoben zurechnen.

Für jede Probe **PASS / FAIL / NOT RUN**, Quellstellen, reproduzierbare Reihenfolge, tatsächliche Messwerte und belastbare Negativkontrollen angeben. **Nichts modifizieren/committen**, auch nicht die Dokumentation oder Engineering-Guardrails. **GUI-NO-GO / Release-NO-GO** bis zur unabhängigen Freigabe und den weiterhin offenen Original-ROM-/DAW-Abnahmen.
