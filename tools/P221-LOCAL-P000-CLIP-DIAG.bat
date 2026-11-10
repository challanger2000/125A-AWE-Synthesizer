@echo off
setlocal DisableDelayedExpansion
title 125A P221 - P000 Originalbank Clip-Diagnose
cd /d "%~dp0"
set "RECORDER=%~dp0125A-P220-VST3-Recorder.exe"
set "DLL=%~dp0125A_AWE_Synthesizer.vst3\Contents\x86_64-win\125A_AWE_Synthesizer.vst3"
if not exist "%RECORDER%" (echo FEHLER: Recorder fehlt.& pause& exit /b 2)
if not exist "%DLL%" (echo FEHLER: Windows-VST3 fehlt.& pause& exit /b 2)
echo.
echo P221 untersucht NUR P000-DRY und P000-MODFX, nicht alle 77.
echo WAV-Fehler werden als originaler UNCLIPPED IEEE-Float gespeichert.
echo KEIN Lautstaerkeabgleich, KEIN automatischer PASS, KEINE Cloud.
echo.
set /p "ROM=Pfad zu awe32.raw: "
set "ROM=%ROM:"=%"
if not exist "%ROM%" (echo ROM fehlt.& pause& exit /b 2)
set /p "SF2=Pfad zu Synth 512 Bank.sf2: "
set "SF2=%SF2:"=%"
if not exist "%SF2%" (echo SF2 fehlt.& pause& exit /b 2)
set "N=1"
:find_free
set "OUTPUT=%~dp0P221-P000-DIAG-%N%"
if exist "%OUTPUT%" (
  set /a N+=1
  if %N% GTR 99 (echo 99 Diagnoseordner vorhanden.& pause& exit /b 2)
  goto find_free
)
mkdir "%OUTPUT%"
if errorlevel 1 (echo Ausgabeordner konnte nicht angelegt werden.& pause& exit /b 2)
"%RECORDER%" "%DLL%" "%ROM%" "%SF2%" "%OUTPUT%" owner-p000-diagnostic > "%OUTPUT%\P221-Recorder-Log.txt" 2>&1
set "RET=%ERRORLEVEL%"
echo.
type "%OUTPUT%\P221-Recorder-Log.txt"
echo.
echo Lokale Diagnose: "%OUTPUT%"
echo Bei echtem Clipping muss der Recorder den betreffenden Test als FAIL
echo bewerten und eine Datei mit Endung FAILED-UNCLIPPED-F32.wav speichern.
echo Dieser Lauf ist KEINE Klang- oder Releaseabnahme.
pause
exit /b %RET%
