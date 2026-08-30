@echo off
setlocal
cd /d "%~dp0"

:: A fresh source checkout does not contain the portable runtime or tools.
:: Hand off to the one-click installer, which opens a new launcher process
:: after setup completes.
if not exist "%~dp0python\python.exe" goto :first_time_setup
if not exist "%~dp0bin\ffmpeg\bin\ffmpeg.exe" goto :first_time_setup
if not exist "%~dp0bin\rubberband\rubberband.exe" goto :first_time_setup
if not exist "%~dp0bin\espeak-ng\libespeak-ng.dll" goto :first_time_setup

:: PATH
set "PATH=%CD%\python;%CD%\python\Scripts;%CD%\python\DLLs;%PATH%"
set "PATH=%CD%\bin\ffmpeg\bin;%CD%\bin\rubberband;%PATH%"

echo.
echo ================================================
echo        LocalSoundsAPI - Launcher
echo ================================================
echo.

"%~dp0python\python.exe" launcher.py

pause
exit /b %ERRORLEVEL%

:first_time_setup
echo.
echo LocalSoundsAPI needs its portable runtime and audio tools.
echo Starting the one-click setup now...
echo.
call "%~dp0install.bat" %*
exit /b %ERRORLEVEL%
