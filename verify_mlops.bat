@echo off
rem Runs scripts\verify_mlops.py with the project Python. Read-only: trains nothing, downloads nothing, pulls no model, runs no candidate code.
rem   verify_mlops.bat                                  integrity, health endpoints, flags, MLflow (if installed)
rem   verify_mlops.bat --url http://127.0.0.1:5000      also probe a running server
rem   verify_mlops.bat --check-docker --check-dvc --check-ollama
rem   verify_mlops.bat --docker-build --docker-run      build the image and run it on 127.0.0.1:5099 (needs Docker Desktop running)
cd /d "%~dp0"
set "PY="
if exist ".bot\Scripts\python.exe" set "PY=.bot\Scripts\python.exe"
if not defined PY if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY set "PY=python"
set "MLFLOW_DISABLE_AGENT_HINT=1"
"%PY%" scripts\verify_mlops.py %*
echo.
if /i not "%SMART_NO_PAUSE%"=="1" pause
