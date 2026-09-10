@echo off
setlocal EnableExtensions
cd /d "%~dp0"
>site-button.log echo STARTED %date% %time%
title Enable Website Refresh Button
echo Connecting the website refresh button to this PC...
if not exist "register_site_button.ps1" goto missing
if not exist "RUN_REFRESH.bat" goto missing
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0register_site_button.ps1" >>site-button.log 2>&1
if errorlevel 1 goto failed
echo.
echo Completed. You can now use the refresh button on the website.
start "" "https://zzunny218.github.io/phjunivcompetitionrate/"
pause
exit /b 0
:missing
>>site-button.log echo FAILED required_files_missing
echo Required files are missing. Extract ALL files from the ZIP first.
goto end
:failed
echo Registration failed. Send site-button.log.
:end
pause
exit /b 1
