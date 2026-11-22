@echo off
chcp 65001 >nul
echo ========================================================
echo       Запуск Backend тестов (Python / PyTest)
echo ========================================================
echo.

if not exist ".venv" (
    echo [!] Виртуальное окружение .venv не найдено. Создание...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

python -c "import pytest" 2>nul
if %errorlevel% neq 0 (
    echo [i] Установка pytest и httpx в .venv...
    pip install pytest httpx
    echo.
)

python -m pytest backend_tests -v

echo.
echo ========================================================
echo           Тестирование Backend завершено!
echo ========================================================
echo.
pause