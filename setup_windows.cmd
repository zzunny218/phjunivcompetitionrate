@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto missing
where gh >nul 2>nul
if errorlevel 1 goto missing
py -3 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt tzdata
if errorlevel 1 goto failed
gh auth status
if errorlevel 1 gh auth login --hostname github.com --web
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -X utf8 windows_sync.py --setup
if errorlevel 1 goto failed
echo Setup completed. Keep this folder. Keep Windows logged in and awake.
pause
exit /b 0
:missing
echo Install Python 3.12 and GitHub CLI first, then open this file again.
pause
exit /b 1
:failed
echo Setup failed. Send windows-sync.log for diagnosis. Do not send passwords or tokens.
pause
exit /b 1
