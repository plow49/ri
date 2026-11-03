@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Run install-windows.cmd first.
 pause
 exit /b 1
)
rem This launcher always uses local SQLite, without Oracle credentials.
set "ERP_DATABASE_URL=sqlite:///erp-local.db"
.venv\Scripts\python.exe app.py
if errorlevel 1 pause
