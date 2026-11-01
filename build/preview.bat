@echo off
REM Serve Ship\docs on http://localhost:8000/ exactly as GitHub Pages will. Close this window to stop.
chcp 65001 >nul
cd /d "%~dp0..\docs"
start "" "http://localhost:8000/"
python -m http.server 8000
