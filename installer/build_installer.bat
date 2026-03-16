@echo off
REM =============================================================================
REM TG-PY Installer Builder - One-Click Build
REM =============================================================================
REM This script builds TG-PY.exe and creates the installer package.
REM 
REM Requirements:
REM   - Python 3.8+ installed
REM   - Inno Setup installed (https://jrsoftware.org/isdl.php)
REM
REM Output:
REM   dist\TG-PY-Setup-v1.0.0.exe  ← Send this to users
REM =============================================================================

setlocal enabledelayedexpansion

echo.
echo ================================================================
echo   TG-PY Installer Builder
echo   Building TG-PY.exe + Installer Package
echo ================================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Get script directory
cd /d "%~dp0"

REM Run the builder
echo Building...
echo.
python installer_builder.py

if errorlevel 1 (
    echo.
    echo ================================================================
    echo   BUILD FAILED
    echo ================================================================
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   BUILD SUCCESS!
echo ================================================================
echo.
echo   Files created:
echo     dist\TG-PY.exe              - Main application
echo     dist\TG-PY-Setup-v1.0.0.exe - Installer (send to users)
echo.
echo   Next Steps:
echo     1. Test TG-PY-Setup-v1.0.0.exe on a clean Windows machine
echo     2. Verify installation and app functionality
echo     3. Distribute to users
echo.
echo   Admin Panel (separate):
echo     Run admin_build.bat to build TG-PY-Admin.exe
echo.
echo ================================================================

REM Open dist folder
if exist "..\dist" (
    explorer "..\dist"
)

pause
