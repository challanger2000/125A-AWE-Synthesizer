@echo off
setlocal
title 125A AWE Synthesizer - Echter ASIO Test
cd /d "%~dp0"
echo.
echo 125A AWE - ECHTER ASIO-TREIBER UND MIDI-AUDIO
echo Bitte andere Audio-Programme beenden und Lautstaerke absenken.
echo Dieser Test aendert keine Windows-Treiber, installiert nichts,
echo speichert keine privaten ROM-/SF2-Dateien und laedt nichts hoch.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P179-ASIO-TEST.ps1"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo ECHTER ASIO-MIDI-Test: PASS.) else (echo ASIO-Test: NO-GO oder nicht ausfuehrbar. Siehe P179-LOCAL-RESULT-*.)
pause
exit /b %RC%
