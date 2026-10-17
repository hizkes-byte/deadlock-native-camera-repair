@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Repair.ps1" -Mode restore
pause
