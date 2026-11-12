@echo off
rem Contract-brief local web UI (thin ASCII shim)
cd /d "%~dp0"
python scripts\server.py
pause
