@echo off
rem Runs the automated tests.
cd /d "%~dp0.."
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt >nul
.venv\Scripts\python.exe -m pytest -q
