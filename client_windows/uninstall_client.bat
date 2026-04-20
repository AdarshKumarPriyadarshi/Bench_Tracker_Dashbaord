@echo off
echo.
echo  =============================================
echo   MBRDI Bench Client - Uninstall (Windows)
echo  =============================================
echo.
set /p CONFIRM="  Remove bench automation from this PC? (yes/no): "
if /i not "%CONFIRM%"=="yes" (
    echo  Cancelled.
    pause
    exit /b 0
)

echo.
echo  [1/4] Stopping processes...
taskkill /f /fi "WINDOWTITLE eq BenchSessionMonitor" >nul 2>&1
taskkill /f /fi "IMAGENAME eq pythonw.exe" >nul 2>&1
echo        Done.

echo  [2/4] Removing scheduled tasks...
schtasks /delete /tn "BenchLoginGate" /f >nul 2>&1
schtasks /delete /tn "BenchSessionMonitor" /f >nul 2>&1
echo        Done.

echo  [3/4] Deleting virtual environment...
cd /d "%~dp0"
if exist venv rmdir /s /q venv
echo        Done.

echo  [4/4] Cleaning logs...
del /q session_monitor.log >nul 2>&1
del /q login_gate.log >nul 2>&1
del /q local_checkins.json >nul 2>&1
echo        Done.

echo.
echo  =============================================
echo   Uninstall Complete!
echo  =============================================
echo.
echo   To reinstall: run setup_client.bat
echo.
pause
