@echo off
setlocal DisableDelayedExpansion
rem P188 Windows: verified ETW permission preflight and one explicitly approved ASIO reference run.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0P188-PREFLIGHT.ps1" %*
set "P188_EXIT=%ERRORLEVEL%"
if not defined CI pause
exit /b %P188_EXIT%
