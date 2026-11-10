@echo off
setlocal DisableDelayedExpansion
title 125A AWE P220 - 77 Originalbank VST3 Audioaufnahmen
cd /d "%~dp0"
set "RECORDER=%~dp0125A-P220-VST3-Recorder.exe"
set "DLL=%~dp0125A_AWE_Synthesizer.vst3\Contents\x86_64-win\125A_AWE_Synthesizer.vst3"
set "OUTPUT=%~dp0P220-PRIVATE-VST3-WAV"
echo.
echo P220: 77 Programme x 2, 154 private VST3-WAV-Dateien.
echo Dies testet den echten VST3-Prozess, NICHT den originalen Win95-Treiber!
echo KEINE 86Box, KEINE Installation, KEIN Internet, KEIN Upload.
echo Originaldateien nur lesen; PCM nur in lokalem Unterordner.
echo.
if not exist "%RECORDER%" (echo FEHLER: Recorder fehlt.& pause& exit /b 2)
if not exist "%DLL%" (echo FEHLER: Gepruefte Windows-VST3-Moduldatei fehlt.& pause& exit /b 2)
set /p "ROM=Pfad zur originalen awe32.raw (ohne Anfuehrungszeichen): "
set "ROM=%ROM:"=%"
if not defined ROM (echo Kein ROM-Pfad.& pause& exit /b 2)
if not exist "%ROM%" (echo ROM-Datei nicht gefunden.& pause& exit /b 2)
set /p "SF2=Pfad zur originalen Synth 512 Bank.sf2 (ohne Anfuehrungszeichen): "
set "SF2=%SF2:"=%"
if not defined SF2 (echo Kein SF2-Pfad.& pause& exit /b 2)
if not exist "%SF2%" (echo SF2-Datei nicht gefunden.& pause& exit /b 2)
if exist "%OUTPUT%" (echo P220-PRIVATE-VST3-WAV bereits vorhanden: kein Ueberschreiben.& pause& exit /b 2)
mkdir "%OUTPUT%"
if errorlevel 1 (echo Ausgabeverzeichnis konnte nicht erzeugt werden.& pause& exit /b 2)
echo.
echo Echte VST3-Audioaufnahmen laufen. Der Original-Win95-Vergleich
echo bleibt OFFEN, bis auch die Original-Creative-PCM-Aufnahmen vorliegen.
echo.
"%RECORDER%" "%DLL%" "%ROM%" "%SF2%" "%OUTPUT%" full >"%OUTPUT%\P220-Recorder-Log.txt" 2>&1
set "RET=%ERRORLEVEL%"
if not "%RET%"=="0" (
 echo P220 VST3 CAPTURE FAIL - siehe "%OUTPUT%\P220-Recorder-Log.txt"
 pause
 exit /b %RET%
)
echo P220 VST3 CAPTURE-FUNKTION DURCHGELAUFEN.
echo Die 154 WAV-Dateien bleiben privat in "%OUTPUT%".
echo KEINE Freigabe / KEIN Creative-Originalvergleich / KEIN Studio One ASIO.
pause
exit /b 0
