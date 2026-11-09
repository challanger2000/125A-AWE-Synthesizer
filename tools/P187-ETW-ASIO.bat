@echo off
setlocal
rem P187: local hardware capture with corrected P186 fail-closed diagnostic export.
rem All native binaries and scripts are verified by the SHA256 package manifest.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0P185-RUN.ps1" %*
set "P187_EXIT=%ERRORLEVEL%"
if not defined CI pause
exit /b %P187_EXIT%
