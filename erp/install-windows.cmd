@echo off
setlocal
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if not errorlevel 1 goto python_ready
where winget >nul 2>&1
if errorlevel 1 (
 echo Install Python 3.12 from https://www.python.org/downloads/windows/ including Tcl/Tk and Python Launcher.
 echo Then run this installer again.
 pause
 exit /b 1
)
echo Python 3.12 is required. Installing with Windows Package Manager...
winget install --id Python.Python.3.12 --exact --source winget --scope user --accept-source-agreements --accept-package-agreements
if errorlevel 1 goto failure
echo Python installation completed. Close this window and run install-windows.cmd again.
pause
exit /b 0
:python_ready
if not exist .venv\Scripts\python.exe py -3.12 -m venv .venv
if errorlevel 1 goto failure
.venv\Scripts\python.exe -m pip install -r requirements-local.txt
if errorlevel 1 goto failure
.venv\Scripts\python.exe -m unittest -v
if errorlevel 1 goto failure
.venv\Scripts\python.exe -c "import tkinter; r=tkinter.Tk(); r.withdraw(); r.destroy()"
if errorlevel 1 goto failure
powershell -NoProfile -Command "$w = New-Object -ComObject WScript.Shell; $s = $w.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'RI ERP.lnk')); $s.TargetPath = [IO.Path]::Combine((Get-Location).Path, 'run-windows.cmd'); $s.WorkingDirectory = (Get-Location).Path; $s.Save()"
if errorlevel 1 (
 echo Shortcut creation failed. You can still use run-windows.cmd.
)
echo Installation completed. Open the RI ERP desktop shortcut or run-windows.cmd.
pause
exit /b 0
:failure
echo Installation or validation failed. Review the output above.
pause
exit /b 1
