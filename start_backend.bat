@echo off
echo ========================================
echo Laser Vibrometry Spy System - Backend
echo ========================================
echo.

echo [1/3] Checking Python environment...
python --version
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.9+
    pause
    exit /b 1
)

echo.
echo [2/3] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

echo.
echo [3/3] Activating environment and starting server...
call venv\Scripts\activate.bat

echo.
echo Installing dependencies (if needed)...
pip install -r requirements.txt

echo.
echo Starting FastAPI server on http://localhost:8000...
echo API docs: http://localhost:8000/docs
echo.
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

pause
