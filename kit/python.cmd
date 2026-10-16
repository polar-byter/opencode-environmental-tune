@echo off
setlocal
rem No Python launcher, registry changes or global PATH changes are needed.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0runtime\bootstrap.ps1" %*
exit /b %errorlevel%
