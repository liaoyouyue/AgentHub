@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Usage: install-universal.cmd ^<codex^|claude^|cursor^|opencode^|generic^|none^>
  echo Example: install-universal.cmd codex
  exit /b 2
)
py -3 adapters\mcp\install_host.py --host %~1
