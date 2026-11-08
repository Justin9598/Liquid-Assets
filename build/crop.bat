@echo off
REM Liquid Assets: the label crop tool (Plan 13). Opens http://127.0.0.1:8765/ in your browser.
REM It only ever writes content\photo-map.json (a backup goes to reports\photo-map-backups first).
REM Close this window to stop it. Then run build.bat to publish the new crops.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
python tools\croptool.py %*
pause
