@echo off
setlocal EnableExtensions
cd /d "%~dp0"
>launcher.log echo STARTED %date% %time%
>>launcher.log echo FOLDER %cd%
title University Competition Rate Refresh
echo.
echo [1/5] Starting...
echo This window will stay open and show the result.
echo.

set "PY_EXE="
set "PY_ARGS="
where py.exe >nul 2>nul
if not errorlevel 1 (
  set "PY_EXE=py.exe"
  set "PY_ARGS=-3"
)
if not defined PY_EXE (
  where python.exe >nul 2>nul
  if not errorlevel 1 set "PY_EXE=python.exe"
)
if not defined PY_EXE (
  for /d %%P in ("%LocalAppData%\Programs\Python\Python3*") do (
    if exist "%%~fP\python.exe" set "PY_EXE=%%~fP\python.exe"
  )
)
if not defined PY_EXE goto python_missing
>>launcher.log echo PYTHON %PY_EXE% %PY_ARGS%
echo [2/5] Python found.

set "GH_EXE="
for /f "delims=" %%G in ('where gh.exe 2^>nul') do if not defined GH_EXE set "GH_EXE=%%G"
if not defined GH_EXE if exist "%ProgramFiles%\GitHub CLI\gh.exe" set "GH_EXE=%ProgramFiles%\GitHub CLI\gh.exe"
if not defined GH_EXE if exist "%LocalAppData%\Programs\GitHub CLI\gh.exe" set "GH_EXE=%LocalAppData%\Programs\GitHub CLI\gh.exe"
if not defined GH_EXE goto gh_missing
set "PH_GH_EXE=%GH_EXE%"
>>launcher.log echo GITHUB_CLI %GH_EXE%
echo [3/5] GitHub CLI found.

if exist ".venv\Scripts\python.exe" goto dependencies
if defined PY_ARGS (
  "%PY_EXE%" %PY_ARGS% -m venv .venv
) else (
  "%PY_EXE%" -m venv .venv
)
if errorlevel 1 goto venv_failed

:dependencies
echo [4/5] Preparing required packages...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r requirements.txt tzdata
if errorlevel 1 goto packages_failed

"%GH_EXE%" auth status >nul 2>nul
if errorlevel 1 (
  echo GitHub login is required. Follow the browser instructions.
  "%GH_EXE%" auth login --hostname github.com --web
)
if errorlevel 1 goto login_failed

echo [5/5] Collecting 17 competition rates...
>>launcher.log echo RUNNING_COLLECTOR
".venv\Scripts\python.exe" -X utf8 windows_sync.py
set "RESULT=%ERRORLEVEL%"
>>launcher.log echo COLLECTOR_EXIT %RESULT%
if not "%RESULT%"=="0" goto collection_failed

echo.
echo Completed. The website may take a few minutes to update.
>>launcher.log echo COMPLETED %date% %time%
start "" "https://zzunny218.github.io/phjunivcompetitionrate/"
pause
exit /b 0

:python_missing
>>launcher.log echo FAILED Python_not_found
echo Python was not found. Reinstall Python and enable "Add Python to PATH".
goto end_failed
:gh_missing
>>launcher.log echo FAILED GitHub_CLI_not_found
echo GitHub CLI was not found. Reinstall GitHub CLI, then restart Windows.
goto end_failed
:venv_failed
>>launcher.log echo FAILED venv_creation
echo Python environment creation failed.
goto end_failed
:packages_failed
>>launcher.log echo FAILED package_install
echo Required package installation failed. Check your internet connection.
goto end_failed
:login_failed
>>launcher.log echo FAILED GitHub_login
echo GitHub login failed.
goto end_failed
:collection_failed
>>launcher.log echo FAILED collector
echo Collection failed. Check windows-sync.log in this folder.
goto end_failed
:end_failed
echo.
echo Send launcher.log and windows-sync.log if it exists.
pause
exit /b 1
