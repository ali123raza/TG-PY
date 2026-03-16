@echo off
SETLOCAL
echo ================================================
echo   TG-PY Fresh Build
echo   Entry: main.py (license check included)
echo   Output: fresh_build/
echo ================================================
echo.

REM Clean old fresh build
IF EXIST fresh_build rmdir /s /q fresh_build
mkdir fresh_build\data
mkdir fresh_build\sessions
mkdir fresh_build\media
mkdir fresh_build\tgdata
mkdir fresh_build\logs

echo [1/2] Building TG-PY.exe...
pyinstaller fresh_tgpy.spec --clean --noconfirm --distpath fresh_build
IF ERRORLEVEL 1 ( echo. & echo [ERROR] Build failed. & pause & exit /b 1 )

echo.
echo [2/2] Build complete!

echo.
echo ================================================
echo   BUILD SUCCESS!
echo   Folder: fresh_build\
echo   Files:
dir /b fresh_build\*.exe | findstr /v "^$"
echo.
echo   IMPORTANT: User ko ye instructions dein:
echo   1. Internet connection required
echo   2. Firewall/antivirus port 5432 allow kare
echo   3. License credentials (username/password) chahiye
echo ================================================
explorer fresh_build
pause
