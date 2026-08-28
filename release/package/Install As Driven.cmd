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

echo Close SimHub before continuing.
echo Windows will ask for administrator approval to install into SimHub.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$script = $env:AS_DRIVEN_SCRIPT; $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ([char]34 + $script + [char]34)); $process = Start-Process -FilePath 'powershell.exe' -Verb RunAs -Wait -PassThru -ArgumentList $arguments; exit $process.ExitCode"
set "AS_DRIVEN_RESULT=%ERRORLEVEL%"

if not "%AS_DRIVEN_RESULT%"=="0" (
    echo.
    echo As Driven was not installed. Review the error above and try again.
    pause
    exit /b %AS_DRIVEN_RESULT%
)

echo.
echo As Driven was installed successfully.
echo Start SimHub and enable As Driven under Settings ^> Plugins.
pause
exit /b 0
