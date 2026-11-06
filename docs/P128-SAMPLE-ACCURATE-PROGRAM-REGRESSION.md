# P128 – reproduzierter MIDI ProgramChange/PCM-Fehler im selben Audioblock

**Ausgangsstand:** `fix/p122-bank-dirty-audit` @ `4bd9787908b24c5b19d8611efe106f9573b2b79c`.

## Fehlernachweis

Unter gleichzeitigem Control-Writer-Gate publiziert die VST3-`process()`-Methode den akzeptierten globalen oder kanalbezogenen ProgramChange-Intent. Nach nicht erfolgter `RealtimeStateVersion::Writer`-Übernahme kehrt `apply()` jedoch direkt zurück. Ein **im selben Audioblock** später eintreffendes NoteOn erklingt deshalb noch mit dem alten Programm, obwohl `getState()` bereits das richtige neu gewählte Programm liefert.

Deterministischer Test mit produktivem `Factory.cpp`-Processor-Quellcode, Original-Steinberg-SDK und öffentlich generierter ROM/SF2:

- [RED #42164394755](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42164394755): globales Programm 9 bei sampleOffset 32, NoteOn bei 64, Writer-Gate verweigert. `written_program=9`, **`pcm_equal=0`** gegenüber gleicher Sequenz ohne Kollision.
- [GREEN #42165261836](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42165261836): **7/7 Assertions PASS**; globale und kanalbezogene Presetwahl liefern bei Writer-Gate-Kollision identische PCM-Samples, und kanalbezogene Override-Masken bleiben erhalten.
- [Vollständige Windows-Regression des isolierten Fixes #42168715268](https://github.com/challanger2000/125A-AWE-Synthesizer/actions/runs/42168715268): **39/39 CTests, 47/47 VST3-Validator, 3/3 EditorHost-Smokes PASS**.
- Die Regression `125A_p128_sample_accurate_program_pcm` testet (a) globales Programm 9, (b) nur Kanal 4 mit Programm 9 und Maskenbit 8, (c) globales Programm 7 plus Kanal 4 Programm 9 mit zwei Noten im selben Block. Jedes Szenario vergleicht Original-PCM gegen identischen Ablauf unter Writer-Contention.

## Gezielte Korrektur

Wenn der schnelle Echtzeit-Writer die Änderung nicht unmittelbar persistieren kann, wird das **bereits angenommene, gestempelte** globale bzw. kanalbezogene Programm **nur im audiothread-eigenen Synth** nachgeführt, damit die folgenden Noten den richtigen Klang erhalten. Die Zustands-Aktualisierung läuft weiterhin über die Pending-Intent-/Recall-Logik, ohne den Control-Gate zu blockieren.

Der kombinierte Entwurf mit dem unabhängigen Master-/GUI-Intent-Fix wird in **Draft PR #65** zusammengeführt und separat voll regressionsgetestet. Produktionsbranch wurde bisher nicht überschrieben.

## Abnahmegrenzen

Dies ist ein echter, reproduzierter Source-derived VST3-Processor-Test unter Windows, nicht eine Bedienungssitzung in Studio One. **Chorus-Hardwareparität, reale ASIO-Zeitbudgets und unabhängiger Gesamt-P128-Audit bleiben offen. Release weiterhin NO-GO.**
