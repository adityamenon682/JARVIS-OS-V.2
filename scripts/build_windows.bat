@echo off
REM Builds a standalone JARVIS.exe under dist\JARVIS.
REM Double-clickable from Explorer; from cmd.exe: scripts\build_windows.bat

setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo [build_windows] No .venv found. Run scripts\setup_jarvis.bat first.
  pause
  exit /b 1
)

echo [build_windows] Installing build dependencies...
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 (
  echo [build_windows] Failed to install requirements-build.txt.
  pause
  exit /b 1
)

.venv\Scripts\python.exe scripts\build_windows.py %*
if errorlevel 1 (
  echo.
  echo JARVIS build failed. Read the message above and try again.
  pause
  exit /b 1
)
pause
