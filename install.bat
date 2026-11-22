@echo off
chcp 65001 >nul
echo ========================================================
echo    Установка зависимостей: Safe AI Patch Orchestrator
echo ========================================================
echo.

:: 1. Проверка и настройка Python venv
echo [1/2] Настройка виртуального окружения Python...
if not exist ".venv" (
    echo Создание .venv...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [+] Python-зависимости успешно установлены.
echo.

:: 2. Установка зависимостей и сборка фронтенда
echo [2/2] Установка Node.js / NPM зависимостей и сборка фронтенда...
cd frontend
call npm install
call npm install pinia lucide-vue-next
call npm install -D vitest @vue/test-utils happy-dom
call npm run build
cd ..

echo.
echo ========================================================
echo    Все зависимости успешно установлены!
echo    Для запуска проекта используйте run.bat
echo ========================================================
echo.
pause