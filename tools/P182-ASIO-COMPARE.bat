@echo off
setlocal
title 125A P182 - Echter ASIO AWE vs MIDI Referenz Test
cd /d "%~dp0"
echo.
echo P182: DREIFACHER ECHTER ASIO REFERENZTEST
echo Reihenfolge: Referenz A - 125A AWE - Referenz B
echo Bitte DAW schliessen und Abhoerlautstaerke niedrig einstellen.
echo Keine Installation. Private ROM und SF2 bleiben ausschliesslich lokal.
echo Ergebnisse sind NUR DIAGNOSE, keine Releasefreigabe.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0P182-ASIO-REFERENCE-COMPARE.ps1"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (echo P182 Dreifach-Vergleich aufgezeichnet. Auswertung in P182-LOCAL-RESULT-*. P181/HARDWARE-RELEASE-GATE unveraendert.) else (echo P182 NO-GO/INCOMPLETE. Siehe P182-LOCAL-RESULT-*.)
pause
exit /b %RC%
