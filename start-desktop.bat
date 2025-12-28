@echo off
echo ========================================
echo      Scoop Easy - Desktop Mode
echo ========================================
echo.

cd /d "%~dp0"

if not exist "frontend\dist\index.html" (
    echo Building frontend...
    cd frontend
    call pnpm build
    if errorlevel 1 (
        echo Frontend build failed!
        pause
        exit /b 1
    )
    cd ..
    echo.
)

echo Starting desktop application...
cd backend
uv run python desktop.py
