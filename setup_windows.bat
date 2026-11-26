@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 x64 first.
  pause
  exit /b 1
)
py -3.11 -m venv .venv
if errorlevel 1 goto failed
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto failed
pip install -r requirements.txt
if errorlevel 1 goto failed
if not exist .env.local copy .env.example .env.local
echo Setup complete. Double-click start_windows.bat to launch the studio.
pause
exit /b 0
:failed
echo Setup failed. Read the error above, then retry.
pause
exit /b 1
