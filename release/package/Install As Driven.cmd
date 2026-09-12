@echo off
setlocal
title Install As Driven

set "AS_DRIVEN_SCRIPT=%~dp0simhub\install.ps1"
if not exist "%AS_DRIVEN_SCRIPT%" (
    echo The As Driven installer is incomplete.
    echo Extract the entire release ZIP before running this file.
    pause
    exit /b 1
)

echo Reminder: close SimHub if it is open. This is not an error message.
echo Windows will ask for administrator approval to install into SimHub.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; try { $script = $env:AS_DRIVEN_SCRIPT; $arguments = @('-NoProfile', '-STA', '-ExecutionPolicy', 'Bypass', '-File', ([char]34 + $script + [char]34), '-Interactive'); $process = Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -PassThru -ArgumentList $arguments; exit $process.ExitCode } catch { Write-Host ('Could not start the installer with administrator approval: ' + $_.Exception.Message); exit 1 }"
set "AS_DRIVEN_RESULT=%ERRORLEVEL%"

if not "%AS_DRIVEN_RESULT%"=="0" (
    echo.
    echo Installation failed. The administrator window shows the actual error
    echo and saves details to an AsDriven-install-error-*.txt file in its TEMP folder.
    echo If that window never opened, check the administrator approval error above.
    pause
    exit /b %AS_DRIVEN_RESULT%
)

echo.
echo As Driven was installed successfully.
echo Start SimHub and enable As Driven under Settings ^> Plugins.
pause
exit /b 0
