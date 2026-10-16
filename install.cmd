@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import tkinter" >nul 2>&1
if errorlevel 1 goto need_python
py -3 "%~dp0install.py"
if errorlevel 1 pause
exit /b
:need_python
echo Python 3.13+ with tkinter is required.
echo Install it from https://www.python.org/downloads/ then run install.cmd again.
echo On Linux: python3 install.py
pause
exit /b 1
