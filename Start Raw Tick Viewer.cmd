@echo off
cd /d "%~dp0"
if not exist ".venv-raw-viewer\Scripts\python.exe" (
  echo Viewer environment missing. See RAW_VIEWER.md for setup.
  pause
  exit /b 1
)
".venv-raw-viewer\Scripts\python.exe" -B plot_raw_ticks.py %*
pause
