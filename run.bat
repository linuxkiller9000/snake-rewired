@echo off
rem SNAKE: REWIRED - Windows launcher.
rem Creates a private .venv on first run (no manual setup needed).
cd /d "%~dp0"
set PY=py -3
%PY% -c "import pygame" 2>nul
if errorlevel 1 (
  if not exist .venv (
    echo First run: setting up a private Python environment...
    %PY% -m venv .venv
    .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
  )
  set PY=.venv\Scripts\python.exe
)
%PY% main.py %*
