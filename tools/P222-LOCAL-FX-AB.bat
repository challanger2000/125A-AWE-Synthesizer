@echo off
setlocal DisableDelayedExpansion
title 125A P222 - kontrollierter FX-A/B-Test
cd /d "%~dp0"
set "RECORDER=%~dp0125A-P220-VST3-Recorder.exe"
set "VST3=%~dp0125A_AWE_Synthesizer.vst3\Contents\x86_64-win\125A_AWE_Synthesizer.vst3"
if not exist "%RECORDER%" (echo FEHLER: VST3-Recorder nicht im Ordner.& pause& exit /b 2)
if not exist "%VST3%" (echo FEHLER: VST3-Modul im Paket fehlt.& pause& exit /b 2)
echo.
echo P222: EINZELN pruefbare FX-Ursache fuer P000 und P021.
echo Fuer JEDE Note/Velocity 48/64 und 72/120:
echo    1 TROCKEN  2 NUR REVERB  3 NUR CHORUS  4 BEIDE.
echo.
echo CC1/7/11/91/93 bleiben je Gruppe identisch.
echo Keine Lautstaerkennormalisierung und kein erneuter 77-Preset-Lauf.
echo Auch bei Clipping bleiben alle 16 originalen Float-WAVs erhalten.
echo Das ist KEIN originaler Creative-Win95-Treibervergleich.
echo.
set /p "ROM=Pfad zu deiner awe32.raw: "
set "ROM=%ROM:"=%"
if not exist "%ROM%" (echo FEHLER: ROM-Datei fehlt.& pause& exit /b 2)
set /p "SF2=Pfad zur Synth 512 Bank.sf2: "
set "SF2=%SF2:"=%"
if not exist "%SF2%" (echo FEHLER: SF2-Datei fehlt.& pause& exit /b 2)
set "N=1"
:find_free
set "OUTPUT=%~dp0P222-PRIVATE-FX-AB-%N%"
if exist "%OUTPUT%" (
  set /a N+=1
  if %N% GTR 99 (echo FEHLER: zu viele vorhandene Ausgaben.& pause& exit /b 2)
  goto find_free
)
mkdir "%OUTPUT%"
if errorlevel 1 (echo FEHLER: Ausgabeordner kann nicht erstellt werden.& pause& exit /b 2)
"%RECORDER%" "%VST3%" "%ROM%" "%SF2%" "%OUTPUT%" fx-factorial > "%OUTPUT%\P222-FX-AB-Log.txt" 2>&1
set "RET=%ERRORLEVEL%"
echo.
type "%OUTPUT%\P222-FX-AB-Log.txt"
echo.
echo Ausgabepfad: "%OUTPUT%"
echo Dateiname ACTUAL-VST3-F32.wav = originale VST3-Prozesswerte,
echo NICHT nachtraeglich entcliptes PCM.
echo Bei Clipping ist Exitcode 1 ein erkannter Fehler, KEIN Test-PASS.
echo 16 Faelle sind nur ein kontrollierter VST3-Versuch.
echo Original-Creative-Klangabnahme bleibt BLOCKED.
pause
exit /b %RET%
