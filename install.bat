@echo off
echo ========================================
echo    Scoop Easy - Install Dependencies
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Installing backend dependencies...
cd backend
uv sync
cd ..

echo.
echo [2/2] Installing frontend dependencies...
cd frontend
pnpm install
cd ..

echo.
echo ========================================
echo    Installation complete!
echo    Run start-dev.bat to start.
echo ========================================
pause
