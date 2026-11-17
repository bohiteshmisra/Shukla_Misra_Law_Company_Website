@echo off
rem One-time setup on Windows: creates the virtual environment, installs packages,
rem creates the database with starter content and prints the admin login.
setlocal
cd /d "%~dp0.."

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

if not exist .venv (
  echo Creating virtual environment...
  %PY% -m venv .venv || goto :fail
)
echo Installing packages...
.venv\Scripts\python.exe -m pip install --upgrade pip >nul
.venv\Scripts\python.exe -m pip install -r requirements.txt || goto :fail

if not exist .env copy .env.example .env >nul
if not exist logs mkdir logs

echo Preparing database...
.venv\Scripts\python.exe -m flask --app wsgi init-db || goto :fail

echo.
echo Setup complete. Start the site with scripts\run.bat
goto :eof

:fail
echo.
echo Setup failed. See the message above.
exit /b 1
