@echo off
setlocal
cd /d "%~dp0"
curl.exe -s --max-time 1 http://127.0.0.1:8765/health >nul 2>&1
if errorlevel 1 (
  start "AgentHub Server" /min cmd.exe /d /c "cd /d %~dp0 && py -3 server.py --port 8765"
  timeout /t 1 /nobreak >nul
)
start "" "http://127.0.0.1:8765/"
exit /b 0