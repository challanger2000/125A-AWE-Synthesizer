# P178 – Benutzerrechner-Abnahme mit privaten Originaldateien

Der P178-Prüfer ist ein **Windows-x64-Testpaket**, kein Plugin-Release.
Er enthält die tatsächlich gebaute AWE-VST3-DLL, `125A-P178-Media-Probe.exe`
und `P178-LOCAL-TEST.bat`. Auf dem Zielrechner sind weder Python noch
Visual Studio, Hyper-V oder eine virtuelle Maschine erforderlich.

## Einmaliger Ablauf

1. Das GitHub-Actions-Artefakt `P178-Windows-PRIVATE-LOCAL-TEST-KIT` entpacken.
2. `P178-LOCAL-TEST.bat` doppelklicken.
3. Den absoluten Pfad zur eigenen `awe32.raw` einfügen und die Pfade zu
   `Synth 512 Bank.sf2`, optional `FM Dreams Sampler.sf2` und
   `Callanish.sf2`. Eine SF2 reicht für den ersten Durchgang.
4. Der Test liest die Originaldaten **nur auf diesem Rechner** und schreibt
   ausschließlich `P178-LOCAL-RESULT.txt` neben die EXE.

### Was nachgewiesen wird

- Die Original-Wave-ROM ist vorhanden und 1 MiB groß (keine Echtheitsprüfung).
- Der Parser liest die wirklichen SF2-Presetnummern und Banknummern aus RIFF/phdr.
  Es werden keine auf 128 ergänzten GM-Einträge als SF2-Presets behauptet.
- Pro SF2-Bank werden der erste, mittlere und letzte tatsächlich vorhandene
  Preset-Eintrag mit der **echten exportierten VST3-DLL** geprüft.
- Unabhängige sofort aktivierte vs. erst nach der Aktivierung geladene SF2
  müssen für dieselbe erste Note **byteidentisches PCM** erzeugen.
- Der Test prüft die erste Note 48 bei Velocity 100, 44,1 kHz,
  8 × 1.024 Frames je Kanal; nicht alle möglichen Tastaturen/Artikulationen.
- Ein echtes 77-Preset-SF2 mit fehlender Bank0-Programmnummer 63 muss bei
  Bank0/Programm63 **vollständig stumm** bleiben, ohne GM-ROM-Fallback.
- Kein Klang wird als korrekt bewertet, wenn das Testpreset für diesen
  MIDI-Ton gar kein Sample auslösen kann: `NOT_VERIFIED` statt PASS.

### Strikte Grenzen

Der Prüfer spielt nicht über ASIO ab, misst keine Hardwaretreue, kontrolliert
nicht jedes Sample-Loop und ersetzt keine echte DAW-Projektsitzung.
Die Original-SF2s und ROM werden weder zur GitHub-Cloud noch zu einem
anderen Server übertragen. Der Prüfer besitzt keine Netzwerkfunktion.
Im öffentlichen CI laufen nur mathematisch erzeugte SoundFonts und eine
synthetische Null-ROM als **Smoke-Test**. Ein öffentlich grünes CI beweist
ausdrücklich **keinen PASS der privaten Originalmedien**.

## Technischer Herkunftsnachweis

- Baseline P177: `f2b07522eab8a364632f88cfcb11f18e18523b40`
- Die geprüften Produkt-Quellen bleiben unverändert, Tests und Paketierung
  liegen ausschließlich auf `qa/p178-private-media-local-acceptance`.
- GitHub Actions Workflow: `.github/workflows/p178-private-media-local-package.yml`.
- CTest-Positive und bewusst negative Probe (fehlende ROM), VST3-Validator.
- NO MERGE, NO FULL AUDIT, NO RELEASE, keine Veröffentlichung privater Daten.
