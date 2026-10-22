@echo off
rem Runs scripts\verify_windows.py with the project's Python. Extra options are passed through, e.g.  verify_windows.bat --url http://127.0.0.1:5000
cd /d "%~dp0"
set "PY="
if exist ".bot\Scripts\python.exe" set "PY=.bot\Scripts\python.exe"
if not defined PY if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY set "PY=python"
"%PY%" scripts\verify_windows.py %*
echo.
pause
