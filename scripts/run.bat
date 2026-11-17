@echo off
rem Starts the website with the production server (waitress).
cd /d "%~dp0.."
if not exist .venv\Scripts\python.exe (
  echo Run scripts\setup.bat first.
  exit /b 1
)
.venv\Scripts\python.exe run_server.py
