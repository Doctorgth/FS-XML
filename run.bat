@echo off
chcp 65001 >nul
echo ========================================================
echo    Запуск Safe AI Patch Orchestrator...
echo ========================================================
echo.

:: 1. Сборка актуального фронтенда
echo [i] Сборка интерфейса...
cd frontend
call npx vite build
if %errorlevel% neq 0 (
    echo [!] Ошибка сборки фронтенда!
    cd ..
    pause
    exit /b 1
)
cd ..

:: 2. Запуск десктопного приложения
echo Запуск окна приложения...
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" desktop_app.py
) else (
    call .venv\Scripts\activate.bat
    start "" python desktop_app.py
)

echo.
echo [+] Приложение Safe AI Patch Orchestrator запущено!
echo.