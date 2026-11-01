@echo off
REM Liquid Assets: regenerate docs/data and docs/img from the ledger and photos (Plan 05).
REM Double-click, or run from a terminal. Extra options (for example --check) are passed through.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
python build.py %*
set RC=%ERRORLEVEL%
if exist "%~dp0..\reports\build-report.html" start "" "%~dp0..\reports\build-report.html"
if not "%RC%"=="0" echo.& echo The build reported errors. docs\data was NOT updated.
echo.
pause
exit /b %RC%
