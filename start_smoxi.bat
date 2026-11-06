@echo off
REM SMOXI Service — always run with project venv (has QR + desktop deps)
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" run.py
) else (
  echo [.venv topilmadi] Avval: python -m venv .venv
  echo Keyin: .venv\Scripts\pip install -r requirements\desktop.txt
  pause
)
