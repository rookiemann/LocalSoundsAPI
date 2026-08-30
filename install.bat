@echo off
setlocal
cd /d "%~dp0"
title LocalSoundsAPI - One-Click Setup

if not exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
    echo.
    echo ERROR: Windows PowerShell is required to install LocalSoundsAPI.
    echo This installer supports 64-bit Windows 10 and Windows 11.
    echo.
    pause
    exit /b 1
)

"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" ^
    -NoLogo -NoProfile -ExecutionPolicy Bypass ^
    -File "%~dp0scripts\install.ps1" %*

set "INSTALL_EXIT_CODE=%ERRORLEVEL%"
if not "%INSTALL_EXIT_CODE%"=="0" (
    echo.
    echo Setup did not complete. Read the error above, then run install.bat again.
    echo An interrupted download will be resumed where possible.
    echo.
    pause
)

exit /b %INSTALL_EXIT_CODE%
