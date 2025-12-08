@echo off
cd /d "%~dp0"

:: PATH
set "PATH=%CD%\python;%CD%\python\Scripts;%CD%\python\DLLs;%PATH%"
set "PATH=%CD%\bin\ffmpeg\bin;%CD%\bin\rubberband;%PATH%"

echo.
echo ================================================
echo        LocalSoundsAPI - Single Instance
echo ================================================
echo.

:: Kill old on 5006
netstat -ano | findstr :5006 | findstr LISTENING >nul && (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5006') do taskkill /F /PID %%a >nul 2>&1
)

echo Starting LocalSoundsAPI on port 5006...
echo   UI + API: http://127.0.0.1:5006
echo.

:: THIS IS THE EXACT WORKING LINE FROM YOUR OLD SUCCESSFUL BUILD — just without the tts_app part
"%~dp0python\python.exe" -c "import sys,pathlib; sys.path.insert(0,str(pathlib.Path('.').resolve())); exec(open('main.py').read())" --port 5006

echo.
echo Server stopped (close window to stop it).
pause