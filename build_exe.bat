@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run py -m venv .venv and install requirements first.
  exit /b 1
)
".venv\Scripts\python.exe" build_exe.py
if errorlevel 1 exit /b %errorlevel%
echo EXE created: dist\JARVIS\JARVIS.exe
