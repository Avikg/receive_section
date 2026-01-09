@echo off
REM WBSEDCL Tracking System - Anaconda Environment Setup for Windows

echo ==========================================
echo WBSEDCL Tracking System - Anaconda Setup
echo ==========================================
echo.

REM Check if conda is available
where conda >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Anaconda/Miniconda not found in PATH
    echo Please install Anaconda or add it to your PATH
    pause
    exit /b 1
)

echo Creating conda environment: wbsedcl_env
echo.

REM Remove existing environment if it exists
conda env remove -n wbsedcl_env -y >nul 2>nul

REM Create new conda environment with Python 3.11
conda create -n wbsedcl_env python=3.11 -y

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create conda environment
    pause
    exit /b 1
)

echo.
echo Environment created successfully!
echo.
echo Activating environment...
call conda activate wbsedcl_env

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to activate environment
    pause
    exit /b 1
)

echo.
echo Installing dependencies...
echo.

REM Upgrade pip first
python -m pip install --upgrade pip

REM Install all requirements
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Environment: wbsedcl_env
echo Python: 3.11
echo.
echo To activate this environment in the future:
echo   conda activate wbsedcl_env
echo.
echo To deactivate:
echo   conda deactivate
echo.
echo To initialize database:
echo   python init_database.py
echo.
echo ==========================================

pause
