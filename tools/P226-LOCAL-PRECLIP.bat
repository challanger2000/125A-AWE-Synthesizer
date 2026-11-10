@echo off
setlocal EnableExtensions DisableDelayedExpansion
title 125A P226 - EMU8000 Originalklang - 32-Bit-Preclip-Analyse
cd /d "%~dp0"
set "PROBE=%~dp0125A-P226-Preclip.exe"
if not exist "%PROBE%" (
  echo FEHLER: 125A-P226-Preclip.exe fehlt in diesem Paket.
  pause
  exit /b 2
)
set "ROM=%~dp0awe32.raw"
if not exist "%ROM%" (
  echo Originale awe32.raw nicht neben dem BAT gefunden.
  set /p "ROM=Vollstaendigen Pfad zu awe32.raw eingeben: "
)
if not exist "%ROM%" (
  echo FEHLER: ROM-Datei existiert nicht.
  pause
  exit /b 2
)
set "SF2=%~dp0Synth 512 Bank.sf2"
if not exist "%SF2%" set "SF2=%~dp0Synth 512 Bank(3).sf2"
if not exist "%SF2%" (
  echo Originale Synth 512 Bank.sf2 nicht neben dem BAT gefunden.
  set /p "SF2=Vollstaendigen Pfad zur Original-SF2 eingeben: "
)
if not exist "%SF2%" (
  echo FEHLER: SoundFont existiert nicht.
  pause
  exit /b 2
)
for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%T"
if not defined STAMP (
  echo FEHLER: Zeitstempel konnte nicht ermittelt werden.
  pause
  exit /b 2
)
set "OUT=%~dp0P226-PRIVATE-%STAMP%"
mkdir "%OUT%" || (
  echo FEHLER: Ergebnisordner konnte nicht erstellt werden.
  pause
  exit /b 2
)
echo Analysiere 16 feste Faelle: Presets 000/021, MIDI N48V64/N72V120,
echo Reverb/Chorus jeweils 0 oder 100. Der Originalklang wird NICHT geaendert.
echo Daten werden NUR lokal gespeichert, nichts wird hochgeladen.
"%PROBE%" "%ROM%" "%SF2%" "%OUT%" --full >"%OUT%\P226-LOG.txt" 2>&1
set "CODE=%ERRORLEVEL%"
type "%OUT%\P226-LOG.txt"
if not "%CODE%"=="0" (
  echo.
  echo P226 FEHLGESCHLAGEN mit Code %CODE%. Unvollstaendige Daten NICHT als PASS werten.
  pause
  exit /b %CODE%
)
set "ZIP=%~dp0P226-PRIVATE-%STAMP%.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%OUT%\*' -DestinationPath '%ZIP%' -ErrorAction Stop"
if errorlevel 1 (
  echo WARNUNG: Die ZIP-Komprimierung schlug fehl. Rohdaten sind in "%OUT%" gesichert.
  pause
  exit /b 1
)
echo.
echo P226 RAW32 ERFASST: 16 Faelle, 44.1 kHz, 32-Bit vor der Begrenzung.
echo Das beweist KEINE Original-Creative-Klangtreue.
echo Ergebnis: "%ZIP%"
echo Nur diese PRIVATE ZIP fuer die Offline-Auswertung bereitstellen.
pause
exit /b 0
