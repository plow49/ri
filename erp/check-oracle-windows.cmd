@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Run install-windows.cmd first.
 pause
 exit /b 1
)
.venv\Scripts\python.exe oracle_check.py
set "erp_check_result=%errorlevel%"
pause
exit /b %erp_check_result%
