@echo off
setlocal
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if not errorlevel 1 goto ready
where winget >nul 2>&1
if errorlevel 1 (
 echo Install Python 3.12 with Tcl/Tk and Python Launcher from python.org and retry.
 pause
 exit /b 1
)
winget install --id Python.Python.3.12 --exact --source winget --scope user --accept-source-agreements --accept-package-agreements
if errorlevel 1 exit /b 1
echo Close this window and run install-windows.cmd again.
pause
exit /b 0
:ready
py -3.12 -m unittest -v
if errorlevel 1 goto fail
py -3.12 -c "import tkinter; r=tkinter.Tk(); r.withdraw(); r.destroy()"
if errorlevel 1 goto fail
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell; $name=[string][char]0xBB3C+[char]0xD488+[char]0xAD00+[char]0xB9AC; $s=$w.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'),$name+'.lnk')); $s.TargetPath=[IO.Path]::Combine((Get-Location).Path,($name+'.cmd')); $s.WorkingDirectory=(Get-Location).Path; $s.IconLocation=[IO.Path]::Combine((Get-Location).Path,'assets\inventory.ico'); $s.Save(); $s=$w.CreateShortcut([IO.Path]::Combine((Get-Location).Path,$name+'.lnk')); $s.TargetPath=[IO.Path]::Combine((Get-Location).Path,($name+'.cmd')); $s.WorkingDirectory=(Get-Location).Path; $s.IconLocation=[IO.Path]::Combine((Get-Location).Path,'assets\inventory.ico'); $s.Save()"
if errorlevel 1 goto fail
echo Installation completed. Open your new desktop shortcut.
pause
exit /b 0
:fail
echo Installation check failed. Review the output above.
pause
exit /b 1
