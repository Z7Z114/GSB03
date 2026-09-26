@echo off
echo ========================================
echo Laser Vibrometry Spy System - Frontend
echo ========================================
echo.

echo [1/3] Checking Node.js environment...
node --version
if errorlevel 1 (
    echo ERROR: Node.js not found! Please install Node.js 18+
    pause
    exit /b 1
)

echo.
echo [2/3] Installing dependencies...
cd frontend
if not exist "node_modules" (
    npm install
    echo Dependencies installed.
) else (
    echo Dependencies already installed.
)

echo.
echo [3/3] Starting development server on http://localhost:5173...
echo.
npm run dev

pause
