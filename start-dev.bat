@echo off
echo ========================================
echo         Scoop Easy - Startup
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Starting backend server...
start "Scoop Easy Backend" cmd /k "cd /d %~dp0backend && uv run python main.py"

echo Waiting for backend...
timeout /t 3 /nobreak > nul

echo.
echo [2/2] Starting frontend server...
echo.
cd /d "%~dp0frontend"
call pnpm dev

echo.
echo Frontend stopped.
pause
