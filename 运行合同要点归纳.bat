@echo off
rem Contract key-point pipeline launcher (thin ASCII shim -> PowerShell)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1" %*
