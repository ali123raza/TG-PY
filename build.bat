@echo off
SETLOCAL
echo ================================================
echo   TG-PY Build Script
echo   Entry: main.py  (app.py no longer needed)
echo ================================================
echo.

python --version >nul 2>&1
IF ERRORLEVEL 1 ( echo [ERROR] Python not found & pause & exit /b 1 )

echo [1/3] Installing dependencies...
pip install -r requirements.txt --quiet
pip install certifi pyinstaller --quiet
IF ERRORLEVEL 1 ( echo [ERROR] Install failed & pause & exit /b 1 )
echo       Done.

echo [2/3] Cleaning old build...
IF EXIST build   rmdir /s /q build
IF EXIST dist    rmdir /s /q dist
echo       Done.

echo [3/3] Building TG-PY.exe...
pyinstaller tgpy.spec --clean --noconfirm
IF ERRORLEVEL 1 ( echo. & echo [ERROR] Build failed. & pause & exit /b 1 )

echo.
echo ================================================
echo   BUILD SUCCESS!
echo   File: dist\TG-PY.exe
echo   Run: dist\TG-PY.exe
echo ================================================
explorer dist
pause