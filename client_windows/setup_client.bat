@echo off
echo.
echo  =============================================
echo   MBRDI Bench Client - Windows Setup
echo  =============================================
echo.

cd /d "%~dp0"

set /p BENCH_ID="  Enter Bench ID (1-5): "
set /p SERVER_IP="  Enter Server IP (e.g., 53.217.60.187): "

echo.
echo  [1/4] Writing config...
echo [server] > config.ini
echo url = http://%SERVER_IP%:8000 >> config.ini
echo timeout = 10 >> config.ini
echo. >> config.ini
echo [bench] >> config.ini
echo bench_id = %BENCH_ID% >> config.ini
echo pc_type = windows >> config.ini
echo        Bench %BENCH_ID% → Server %SERVER_IP%

echo  [2/4] Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found. Install Python and add to PATH.
    pause
    exit /b 1
)

echo  [3/4] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet

echo  [4/4] Creating scheduled task...
set "VENV_PYTHON=%~dp0venv\Scripts\pythonw.exe"
schtasks /delete /tn "BenchLoginGate" /f >nul 2>&1
schtasks /create /tn "BenchSessionMonitor" /tr "\"%VENV_PYTHON%\" \"%~dp0session_monitor.py\"" /sc onstart /rl highest /f >nul 2>&1
echo        Session monitor task created.

echo.
echo  =============================================
echo   Setup Complete!
echo  =============================================
echo.
echo   Session monitor runs on startup (handles login gate automatically).
echo.
echo   To test now:
echo     venv\Scripts\python.exe login_gate.py
echo.
pause
