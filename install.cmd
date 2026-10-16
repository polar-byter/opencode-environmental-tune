@echo off
setlocal
cd /d "%~dp0"
call "%~dp0kit\python.cmd" "%~dp0install.py"
set "kit_result=%errorlevel%"
if not "%kit_result%"=="0" pause
exit /b %kit_result%
