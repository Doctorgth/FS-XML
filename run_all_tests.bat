@echo off
chcp 65001 >nul
echo ========================================================
echo     ПОЛНЫЙ ПРОГОН ВСЕХ ТЕСТОВ (Backend + Frontend)
echo ========================================================
echo.

echo [1/2] Запуск Backend тестов (Python / PyTest)...
call .venv\Scripts\activate.bat
python -m pytest backend_tests -v
if %errorlevel% neq 0 (
    echo [!] Ошибка в Backend тестах!
    pause
    exit /b 1
)

echo.
echo [2/2] Запуск Web тестов (Vue 3 / TypeScript / Vitest)...
cd frontend
call npm run test
if %errorlevel% neq 0 (
    echo [!] Ошибка в Web тестах!
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo ========================================================
echo      ВСЕ ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ (100%% GREEN)!
echo ========================================================
echo.
pause