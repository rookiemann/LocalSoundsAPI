@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

:: PATH setup
set "PATH=%CD%\python;%CD%\python\Scripts;%CD%\python\DLLs;%PATH%"
set "PATH=%CD%\bin\ffmpeg\bin;%CD%\bin\rubberband;%PATH%"

echo.
echo ================================================
echo     LocalSoundsAPI - MULTI INSTANCE LAUNCHER
echo ================================================
echo.

:ask_count
set "count="
set /p "count=How many instances (1-20)? "
if not defined count goto ask_count
echo %count%| findstr /r "^[1-9][0-9]*$" >nul || goto ask_count
if %count% GTR 20 set count=20

:ask_port
set "baseport="
set /p "baseport=Starting port (e.g. 5000)? "
if not defined baseport goto ask_port
echo %baseport%| findstr /r "^[0-9][0-9]*$" >nul || goto ask_port

echo.
echo Starting %count% instances on ports %baseport% - %=%baseport%+%count%-1%...

:: Kill old processes on these ports
set /a lastport=baseport+count-1
for /L %%p in (%baseport%,1,%lastport%) do (
    netstat -ano | findstr ":%%p " | findstr LISTENING >nul && (
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%p "') do taskkill /F /PID %%a >nul 2>&1
    )
)

:: Launch instances
set /a end=count-1
for /L %%i in (0,1,%end%) do (
    set /a port=baseport+%%i
    echo   Launching instance on port !port!

    :: === THE FIX: use CALL and %%port%% or write with delayed expansion off temporarily ===
    set "tempbat=%temp%\lsa_!port!_%random%.bat"
    (
        echo @echo off
        echo title LocalSoundsAPI - !port!
        echo cd /d "%~dp0"
        echo set "PATH=%CD%\python;%CD%\python\Scripts;%CD%\python\DLLs;%PATH%"
        echo set "PATH=%CD%\bin\ffmpeg\bin;%CD%\bin\rubberband;%PATH%"
        echo "%~dp0python\python.exe" -c "import sys,pathlib; sys.path.insert(0,str(pathlib.Path('.').resolve())); exec(open('main.py').read())" --port !port!
        echo echo.
        echo echo Server on http://127.0.0.1:!port!
        echo echo Press Ctrl+C to stop this instance
        echo pause
    ) > "!tempbat!"

    start "LocalSoundsAPI - !port!" cmd /k "!tempbat!"
)

echo.
echo ================================================
echo SUCCESS: %count% instances launched!
echo ================================================
for /L %%i in (0,1,%end%) do (
    set /a port=baseport+%%i
    echo   http://127.0.0.1:!port!
)
echo.
echo Close any window ^(or Ctrl+C^) to stop that instance.
echo.
pause