@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto missing
where gh >nul 2>nul
if errorlevel 1 goto missing
if exist ".venv\Scripts\python.exe" goto ready
py -3 -m venv .venv
if errorlevel 1 goto failed
:ready
".venv\Scripts\python.exe" -m pip install -r requirements.txt tzdata
if errorlevel 1 goto failed
gh auth status
if errorlevel 1 gh auth login --hostname github.com --web
if errorlevel 1 goto failed
echo Collecting competition rates. Please wait...
".venv\Scripts\python.exe" -X utf8 windows_sync.py
if errorlevel 1 goto failed
echo Results uploaded. Some sources may have failed; see the website for each status.
start "" "https://zzunny218.github.io/phjunivcompetitionrate/"
pause
exit /b 0
:missing
echo Install Python 3.12 and GitHub CLI first, then reopen this file.
pause
exit /b 1
:failed
echo Collection failed or is already running. Check windows-sync.log.
pause
exit /b 1
