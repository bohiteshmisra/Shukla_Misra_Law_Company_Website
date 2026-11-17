@echo off
rem Resets the admin password to a new temporary one and clears any lockout.
cd /d "%~dp0.."
.venv\Scripts\python.exe -m flask --app wsgi reset-admin
