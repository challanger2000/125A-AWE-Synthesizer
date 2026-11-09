@echo off
setlocal DisableDelayedExpansion
rem P189: real ETW privilege preflight, then one explicit ASIO reference session with detailed TDH error provenance.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0P188-PREFLIGHT.ps1" %*
set "P189_EXIT=%ERRORLEVEL%"
if not defined CI pause
exit /b %P189_EXIT%
