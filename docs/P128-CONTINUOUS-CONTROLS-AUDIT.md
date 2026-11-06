# P128 – unabhängig reproduzierter Master-/GUI-Zustandsverlust

**Status 2026-11-06:** Kandidat für reviewbare Integration, **kein Release-GO**.

## Nachweis / Root Cause

Auf dem verbindlichen P128-Processorstand `9d97ed9249d5c696865c581181b7cd2e310821de` wurde ein reproduzierbarer Datenverlust gefunden. Bei zeitgleichem Control-Writer-Gate nimmt `process()` persistenten `kVolumeID`- und `kGuiFirstID`-Parameter an, gibt aber vor der dauerhaften Speicherung zurück. Anders als Bank/Programm besaßen diese Parameter vorher keine Pending-Intents. Die ursprünglich gespeicherten Werte 6200 (Master) / 2200 (GUI #0) blieben auch nach einem Folgeblock bestehen, obwohl 3500 / 7500 angenommen wurden.

- **RED, unabhängig instrumentierter Windows-Processor aus `Factory.cpp`:** [#42162242908](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42162242908), `RESULT checks=4 failed=3`; positive Kontrolle ohne Kollision PASS, verlorene Master-/GUI-Werte FAIL.
- **GREEN, isolierter Fixkandidat:** [#42162630394](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42162630394), `RESULT checks=4 failed=0`.
- **Erweiterte GREEN-Matrix:** [#42162850980](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42162850980), `RESULT checks=10 failed=0`: Master + 12 unabhängige GUI-Werte; sofortiger Save und Folgeblock; neuere Recalls verdrängen ältere Werte; nach Recall-Start angenommene Werte überleben dessen Commit.
- **Prüfstand:** Kein nachgebautes Audiomodell: Der tatsächliche Processor wird aus der bestehenden `Factory.cpp` für die native Windows-SDK-Testkomponente extrahiert, und die V10-Streams werden mit der echten `AssetState`-Serialisierung geprüft. Der Prüfbinary ist **nicht identisch mit der exportierten VST3-DLL**; eine zusätzliche reale VST3-Hostprüfung und DAW-Abnahme sind erforderlich.

## Korrektur

Akzeptierte Master-/GUI-Eingaben werden vor dem nichtblockierenden RT Writer als atomare `uint64_t`-Intents mit gemeinsamer monotoner Ereignissequenz erfasst. Die unteren 14 Bits kodieren die vorhandene State-Skala 0…10000, das restliche Wort die Ereignisreihenfolge. Die bestehenden Replay-/Recall-Muster werden ohne Audiomutex, Heap-Allokation und unbeschränkte Retry-Schleifen fortgesetzt:

- `getState()` berücksichtigt angenommene, noch nicht angewendete Werte; doppelte Intentaufnahme in die vorhandene optimistische Zustandsaufnahme integriert.
- `setState()` übernimmt nur nach dem Recall-Start akzeptierte Master-/GUI-Änderungen; ein jüngerer Recall verdrängt ältere Intents.
- `process()` legt Pending-Werte nach Writer-Freigabe sowie nach Enginewechsel nach. Eine erneute Prüfung **innerhalb** der Writer-Ownership verhindert das Wiedereinspielen alter Werte nach neueren Recalls.
- P128-Stateformat **V10**, Controller-Parameter-IDs, ROM-Verpflichtung und 28-MiB-Limit bleiben unverändert.
- Dauerhafte Regression: `125A_p128_persistent_controls`, `tests/p128_processor_order.cpp`; über `tests/p128_processor.cmake` in die Windows-CTests eingebunden.

## Offene Abnahme

Nicht nachgewiesen: reale DAW-Automation samt Aufnahme/Wiedergabe, hardwaregetreue PCM-/Effektparität, vollständige Produkt-GUI und ASIO-Deadlines. Der unabhängige P128-Nachaudit und die übrigen Befunde aus GitHub Issue #64 bleiben offen. **Keine Veröffentlichung auf Basis dieses einen Fixes.**
