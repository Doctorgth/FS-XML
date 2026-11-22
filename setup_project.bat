@echo off
chcp 65001 >nul
echo ========================================================
echo    Развертывание проекта: Safe AI Patch Orchestrator
echo ========================================================
echo.

:: 1. Создание серверной структуры и ядра Core
echo [1/4] Создание структуры папок Core и Server...

mkdir core
mkdir core\handlers
mkdir core\handlers\system_standard
mkdir core\handlers\system_management
mkdir core\handlers\custom

mkdir server
mkdir server\database
mkdir server\services
mkdir server\middlewares
mkdir server\api

:: Создаем заглушки __init__.py для Python
type nul > core\__init__.py
type nul > core\engine.py
type nul > core\registry.py
type nul > core\sandbox.py
type nul > core\types.py
type nul > core\handlers\__init__.py
type nul > core\handlers\base.py
type nul > core\handlers\system_standard\__init__.py
type nul > core\handlers\system_standard\create.py
type nul > core\handlers\system_standard\edit.py
type nul > core\handlers\system_management\__init__.py
type nul > core\handlers\system_management\profile_create.py
type nul > core\handlers\system_management\file_state.py
type nul > core\handlers\custom\__init__.py
type nul > core\handlers\custom\example_aboba.py

type nul > server\__init__.py
type nul > server\main.py

:: Создаем базовые файлы конфигурации
echo node_modules/ > fsignore_global
echo .git/ >> fsignore_global
echo .venv/ >> fsignore_global
echo __pycache__/ >> fsignore_global
echo dist/ >> fsignore_global
echo context_dump.txt >> fsignore_global

type nul > FS-XML.txt

echo [+] Структура Core и Server успешно создана.
echo.

:: 2. Развертывание фронтенда на Vite + Vue 3 + TypeScript
echo [2/4] Развертывание Vue 3 + TypeScript через Vite...

call npm create vite@latest frontend -- --template vue-ts

cd frontend

echo.
echo [3/4] Установка зависимостей фронтенда (Pinia, Lucide Icons, TailwindCSS)...
call npm install
call npm install pinia lucide-vue-next
call npm install -D tailwindcss postcss autoprefixer
call npx tailwindcss init -p

:: 3. Настройка Tailwind и архитектуры папок во фронтенде
echo.
echo [4/4] Создание Feature-Sliced архитектуры во фронтенде...

mkdir src\app
mkdir src\widgets
mkdir src\widgets\FileTree
mkdir src\widgets\ExecutionHub
mkdir src\widgets\HistoryPanel
mkdir src\features
mkdir src\features\manage-profiles
mkdir src\features\filter-files
mkdir src\features\run-execution
mkdir src\entities
mkdir src\shared
mkdir src\shared\api
mkdir src\shared\ui

:: Перезаписываем tailwind.config.js правильными путями
(
echo /** @type {import('tailwindcss'^).Config} */
echo export default {
echo   content: [
echo     "./index.html",
echo     "./src/**/*.{vue,js,ts,jsx,tsx}",
echo   ],
echo   theme: {
echo     extend: {},
echo   },
echo   plugins: [],
echo }
) > tailwind.config.js

:: Добавляем директивы Tailwind в style.css
(
echo @tailwind base;
echo @tailwind components;
echo @tailwind utilities;
) > src\style.css

cd ..

echo.
echo ========================================================
echo    Проект успешно настроен и готов к разработке!
echo ========================================================
echo.
echo Для запуска фронтенда:
echo   cd frontend
echo   npm run dev
echo.
pause