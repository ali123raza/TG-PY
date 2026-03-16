@echo off
echo ================================================
echo   TG-PY Admin Panel Build
echo ================================================

pip install certifi pyinstaller --quiet

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "TG-PY-Admin" ^
    --add-data "license;license" ^
    --collect-all psycopg2 ^
    --hidden-import psycopg2 ^
    --hidden-import psycopg2._psycopg ^
    --hidden-import psycopg2.extensions ^
    --hidden-import bcrypt ^
    --hidden-import _bcrypt ^
    --hidden-import certifi ^
    --hidden-import PyQt6 ^
    --clean --noconfirm ^
    admin_panel/main.py

IF ERRORLEVEL 1 ( echo [ERROR] Build failed. & pause & exit /b 1 )

echo.
echo ================================================
echo   Admin Panel: dist\TG-PY-Admin.exe
echo ================================================
pause