@echo off
setlocal DisableDelayedExpansion
rem P189: Read previously saved ETL only, never start new ETW, ASIO or audio.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0P189-REPLAY.ps1" %*
set "P189_EXIT=%ERRORLEVEL%"
if not defined CI pause
exit /b %P189_EXIT%
