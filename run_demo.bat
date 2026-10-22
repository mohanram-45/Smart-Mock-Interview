@echo off
rem SMART Mock Interview - one-click local launcher (Windows). Starts the app on this computer only and opens the demo in your browser.
rem   run_demo.bat                 normal start (experimental features OFF)
rem   run_demo.bat --code-check    also offer the experimental code check (read-only: code is NOT run)
rem   run_demo.bat --live-model          also offer the experimental concept check with the local Ollama model (slow; results are not validated)
rem   run_demo.bat --docker        code check + sandboxed behaviour tests; needs Docker Desktop and the image built once (see docs\CONFIGURATION.md)
setlocal
cd /d "%~dp0"
set "PY="
if exist ".bot\Scripts\python.exe" set "PY=.bot\Scripts\python.exe"
if not defined PY if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY set "PY=python"

"%PY%" --version >nul 2>&1
if errorlevel 1 goto nopython
"%PY%" -c "import flask, flask_cors" >nul 2>&1
if errorlevel 1 goto nopackages

if "%SMART_PORT%"=="" set "SMART_PORT=5000"
netstat -ano | findstr /R /C:":%SMART_PORT% .*LISTENING" >nul
if not errorlevel 1 goto portbusy

:args
if "%~1"=="" goto go
if /I "%~1"=="--code-check" set "SMART_DEMO_CODE_EVAL=1"
if /I "%~1"=="--live-model" set "SMART_DEMO_LIVE_MODULAR=1"
if /I "%~1"=="--docker" (
  set "SMART_DEMO_CODE_EVAL=1"
  set "SMART_CODEEVAL_EXEC=docker"
)
shift
goto args

:go
echo.
echo  SMART Mock Interview  -  http://127.0.0.1:%SMART_PORT%/demo/
echo  Using: %PY%
if defined SMART_DEMO_LIVE_MODULAR echo  Experimental local-model concept check: ON (needs Ollama running; not validated)
if defined SMART_DEMO_CODE_EVAL echo  Experimental code check: ON
if defined SMART_CODEEVAL_EXEC echo  Sandboxed code execution requested: %SMART_CODEEVAL_EXEC% (used only if its self-test passes)
echo  Close this window or press Ctrl+C to stop.
echo.
start "" /b "%PY%" -c "import time,webbrowser;time.sleep(6);webbrowser.open('http://127.0.0.1:%SMART_PORT%/demo/')"
"%PY%" main\app.py
goto end

:nopython
echo Python was not found. Create the environment first - see README.md, "Windows quick start".
goto end
:nopackages
echo Flask is not installed in %PY%. Run:   %PY% -m pip install -r requirements.txt
goto end
:portbusy
echo Port %SMART_PORT% is already in use - the app may already be running at http://127.0.0.1:%SMART_PORT%/demo/
echo To use another port:  set SMART_PORT=5001   then run this file again.
:end
echo.
pause
