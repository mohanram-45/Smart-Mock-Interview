@echo off
title SMART Mock Interview - Launcher
set ROOT=%~dp0

echo Starting Ollama, main backend, frontend, and compare tool...
echo.

netstat -ano | findstr :11434 >nul
if %errorlevel%==0 (
    echo Ollama already running on port 11434 - skipping.
) else (
    start "Ollama" cmd /k "ollama serve"
)

start "Main Backend - port 5000" cmd /k "cd /d %ROOT%main && call %ROOT%.bot\Scripts\activate.bat && python app.py"

start "Frontend - port 3000" cmd /k "cd /d %ROOT%frontend && node server.js"

start "Compare Tool - port 5050" cmd /k "cd /d %ROOT%compare && call %ROOT%.bot\Scripts\activate.bat && python app.py"

echo.
echo All services launching in separate windows.
echo Main app:     http://localhost:3000
echo Compare tool: http://localhost:5050  (or use the "Compare Models" button)
echo.
pause
