@echo off
setlocal DisableDelayedExpansion
title 125A AWE Synthesizer - Private Original-Media Acceptance
cd /d "%~dp0"
set "PROBE=%~dp0125A-P178-Media-Probe.exe"
set "DLL=%~dp0125A_AWE_Synthesizer.vst3\Contents\x86_64-win\125A_AWE_Synthesizer.vst3"
if not exist "%PROBE%" (echo FEHLER: Test-EXE fehlt.& pause& exit /b 2)
if not exist "%DLL%" (echo FEHLER: Windows VST3-Binaerdatei fehlt.& pause& exit /b 2)
echo.
echo 125A AWE - ORIGINAL-ROM UND ORIGINAL-SF2, NUR LOKAL
echo Kein Python, keine VM, kein Upload, keine Installation.
echo Pfade OHNE Anfuehrungszeichen einkopieren.
echo.
set /p "ROM=Pfad zu deiner originalen awe32.raw: "
set "ROM=%ROM:"=%"
if not defined ROM (echo Kein ROM-Pfad.& pause& exit /b 2)
set /p "SF2A=Pfad zu Synth 512 Bank.sf2 (oder anderer erster SF2): "
set "SF2A=%SF2A:"=%"
if not defined SF2A (echo Kein SF2-Pfad.& pause& exit /b 2)
set /p "SF2B=Zweiter SF2-Pfad (Enter = ueberspringen): "
set "SF2B=%SF2B:"=%"
set /p "SF2C=Dritter SF2-Pfad (Enter = ueberspringen): "
set "SF2C=%SF2C:"=%"
echo.
echo Originaldateien werden nur gelesen, niemals kopiert oder hochgeladen.
echo Das Testergebnis steht nach Abschluss in P178-LOCAL-RESULT.txt.
echo.
if defined SF2C goto THREE
if defined SF2B goto TWO
"%PROBE%" "%DLL%" "%ROM%" "%SF2A%"
goto RESULT
:TWO
"%PROBE%" "%DLL%" "%ROM%" "%SF2A%" "%SF2B%"
goto RESULT
:THREE
if not defined SF2B (echo Bitte erst die zweite SF2 angeben.& pause& exit /b 2)
"%PROBE%" "%DLL%" "%ROM%" "%SF2A%" "%SF2B%" "%SF2C%"
:RESULT
set "RET=%ERRORLEVEL%"
echo.
if "%RET%"=="0" (
  echo TESTERGEBNIS: Gepruefte Faelle PASS. Original-Hardwaretreue/ASIO nicht beurteilt.
) else if "%RET%"=="3" (
  echo TEILERGEBNIS: Mindestens ein Preset beim Testton nicht verifiziert.
) else (
  echo TESTERGEBNIS: FAIL oder nicht ausfuehrbar. Bericht kontrollieren.
)
echo Bericht: %~dp0P178-LOCAL-RESULT.txt
pause
exit /b %RET%
