@echo off
echo Starting OCR Application...
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first to create the virtual environment.
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Set environment variables
set PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

REM Run the application
python main.py

REM Pause only if there was an error
if %errorlevel% neq 0 (
    echo.
    echo Application exited with error.
    pause
)
