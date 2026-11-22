@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo    Настройка Embed Python и установка зависимостей
echo ========================================================
echo.

if not exist "python\python.exe" (
    echo [!] Не найден файл python\python.exe
    echo     Убедитесь, что папка embed Python называется "python" и лежит в корне проекта.
    pause
    exit /b 1
)

:: 1. Включение import site в файле *._pth
echo [1/3] Настройка *._pth (включение import site)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$pthFiles = Get-ChildItem -Path 'python' -Filter '*._pth' -File; " ^
  "if (-not $pthFiles) { Write-Host '[!] Файл *._pth не найден в папке python'; exit 1 }; " ^
  "foreach ($f in $pthFiles) { " ^
  "  $text = [System.IO.File]::ReadAllText($f.FullName); " ^
  "  if ($text -match '(?m)^#\s*import\s+site(?=\r?$)') { " ^
  "    $text = $text -replace '(?m)^#\s*import\s+site(?=\r?$)', 'import site' " ^
  "  } elseif ($text -notmatch '(?m)^import\s+site(?=\r?$)') { " ^
  "    $text = $text.TrimEnd() + [Environment]::NewLine + 'import site' + [Environment]::NewLine " ^
  "  }; " ^
  "  [System.IO.File]::WriteAllText($f.FullName, $text, [System.Text.UTF8Encoding]::new($false)); " ^
  "  Write-Host ('[+] Обновлен файл: ' + $f.Name) " ^
  "}"
if errorlevel 1 (
    echo [!] Ошибка при настройке *._pth!
    pause
    exit /b 1
)
echo.

:: 2. Скачивание и установка pip
echo [2/3] Проверка и установка pip...
python\python.exe -m pip --version >nul 2>&1
if not errorlevel 1 (
    echo [+] pip уже установлен.
    goto :install_deps
)

echo [i] Скачивание get-pip.py...
curl -fsSL -o "python\get-pip.py" "https://bootstrap.pypa.io/get-pip.py" >nul 2>&1
if errorlevel 1 (
    echo [i] Повторная попытка скачивания через PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile 'python\get-pip.py'"
)

if not exist "python\get-pip.py" (
    echo [!] Не удалось скачать get-pip.py! Проверьте подключение к интернету.
    pause
    exit /b 1
)

echo [i] Установка pip в embed Python...
python\python.exe "python\get-pip.py" --no-warn-script-location
if errorlevel 1 (
    echo [!] Ошибка установки pip!
    del /q "python\get-pip.py" >nul 2>&1
    pause
    exit /b 1
)
del /q "python\get-pip.py" >nul 2>&1

:install_deps
echo.

:: 3. Установка зависимостей из requirements.txt
echo [3/3] Установка зависимостей из requirements.txt...
if not exist "requirements.txt" (
    echo [!] Файл requirements.txt не найден в корне проекта!
    pause
    exit /b 1
)

echo [i] Обновление pip и установка setuptools / wheel...
python\python.exe -m pip install --no-warn-script-location --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [!] Ошибка установки setuptools / wheel!
    pause
    exit /b 1
)

echo [i] Установка зависимостей проекта...
python\python.exe -m pip install --no-warn-script-location --no-build-isolation -r requirements.txt
if errorlevel 1 (
    echo [!] Ошибка установки зависимостей!
    pause
    exit /b 1
)

echo.
echo ========================================================
echo    Embed Python успешно настроен и зависимости установлены!
echo ========================================================
echo.
pause