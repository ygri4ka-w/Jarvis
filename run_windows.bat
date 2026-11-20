@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run py -m venv .venv and install requirements first.
  exit /b 1
)
".venv\Scripts\python.exe" main.py
