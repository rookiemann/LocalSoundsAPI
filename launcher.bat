@echo off
cd /d "%~dp0"

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
