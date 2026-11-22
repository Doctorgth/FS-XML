@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo    Сборка релиза FS-XML Interpreter в папку release\
echo ========================================================
echo.

if not exist "python\python.exe" (
    echo [!] Не найден embed Python в папке python\
    pause
    exit /b 1
)

if not exist "launcher.cs" (
    echo [!] Не найден файл launcher.cs!
    pause
    exit /b 1
)

if not exist "desktop_app.py" (
    echo [!] Не найден файл desktop_app.py!
    pause
    exit /b 1
)

:: 1. Сборка актуального фронтенда
echo [1/4] Сборка фронтенда ^(frontend\dist^)...
pushd frontend
call npx vite build
if errorlevel 1 (
    popd
    echo [!] Ошибка сборки фронтенда!
    pause
    exit /b 1
)
popd

if not exist "frontend\dist\index.html" (
    echo [!] Папка frontend\dist не собрана!
    pause
    exit /b 1
)
echo [+] Фронтенд собран.
echo.

:: 2. Компиляция FS-XML.exe из launcher.cs
echo [2/4] Компиляция FS-XML.exe...
set "CSC_PATH="
if exist "%SystemRoot%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" (
    set "CSC_PATH=%SystemRoot%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
) else if exist "%SystemRoot%\Microsoft.NET\Framework\v4.0.30319\csc.exe" (
    set "CSC_PATH=%SystemRoot%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
)

if not defined CSC_PATH (
    for /f "delims=" %%I in ('where csc.exe 2^>nul') do (
        set "CSC_PATH=%%I"
        goto :csc_ready
    )
)

:csc_ready
if not defined CSC_PATH (
    echo [!] Не найден компилятор csc.exe ^(.NET Framework 4.x^).
    pause
    exit /b 1
)

set "PLATFORM=x64"
for /f "usebackq delims=" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$dll = Get-ChildItem -Path 'python' -Filter 'python3*.dll' | Where-Object { $_.Name -match '^python3\d+\.dll$' } | Select-Object -First 1; if (-not $dll) { Write-Output 'x64'; exit 0 }; $fs = [System.IO.File]::OpenRead($dll.FullName); $br = New-Object System.IO.BinaryReader($fs); $fs.Seek(0x3C, 'Begin') | Out-Null; $pe = $br.ReadInt32(); $fs.Seek($pe + 4, 'Begin') | Out-Null; $machine = $br.ReadUInt16(); $br.Close(); $fs.Close(); if ($machine -eq 0x014c) { Write-Output 'x86' } else { Write-Output 'x64' }"`) do (
    set "PLATFORM=%%A"
)

set "ICON_ARG="
if exist "images\FS-XML.ico" (
    set "ICON_ARG=/win32icon:images\FS-XML.ico"
) else (
    echo [!] Внимание: images\FS-XML.ico не найден, сборка без иконки.
)

"%CSC_PATH%" /nologo /optimize+ /target:winexe /platform:%PLATFORM% %ICON_ARG% /reference:System.Windows.Forms.dll /out:FS-XML.exe launcher.cs
if errorlevel 1 (
    echo [!] Ошибка компиляции FS-XML.exe!
    pause
    exit /b 1
)
echo [+] FS-XML.exe скомпилирован ^(%PLATFORM%^).
echo.

:: 3. Подготовка папки release\
echo [3/4] Подготовка папки release\...
if exist "release" (
    rmdir /s /q "release"
    if exist "release" (
        echo [!] Не удалось очистить старую папку release\. Закройте запущенный FS-XML.exe и повторите.
        pause
        exit /b 1
    )
)
mkdir "release"

:: 4. Копирование файлов релиза
echo [4/4] Копирование файлов проекта и Embed Python в release\...

copy /y "FS-XML.exe" "release\" >nul || goto :copy_error
copy /y "desktop_app.py" "release\" >nul || goto :copy_error
copy /y "FS-XML.txt" "release\" >nul || goto :copy_error
if exist "LICENSE" copy /y "LICENSE" "release\" >nul || goto :copy_error
if exist "NOTICE.md" copy /y "NOTICE.md" "release\" >nul || goto :copy_error

if exist "fsignore_global" (
    copy /y "fsignore_global" "release\" >nul || goto :copy_error
) else (
    (
        echo node_modules/
        echo .git/
        echo .venv/
        echo __pycache__/
        echo dist/
        echo context_dump.txt
    ) > "release\fsignore_global"
)

robocopy "core" "release\core" /E /XD __pycache__ .pytest_cache /XF *.pyc *.pyo /NFL /NDL /NJH /NJS /NC /NS /NP
if errorlevel 8 goto :copy_error

robocopy "server" "release\server" /E /XD __pycache__ .pytest_cache /XF *.pyc *.pyo /NFL /NDL /NJH /NJS /NC /NS /NP
if errorlevel 8 goto :copy_error

robocopy "frontend\dist" "release\frontend\dist" /E /NFL /NDL /NJH /NJS /NC /NS /NP
if errorlevel 8 goto :copy_error

if exist "images" (
    robocopy "images" "release\images" /E /NFL /NDL /NJH /NJS /NC /NS /NP
    if errorlevel 8 goto :copy_error
)

robocopy "python" "release\python" /E /XD __pycache__ /XF *.pyc *.pyo get-pip.py /NFL /NDL /NJH /NJS /NC /NS /NP
if errorlevel 8 goto :copy_error

echo.
echo ========================================================
echo    Релиз успешно собран в папке: release\
echo    Для запуска используйте: release\FS-XML.exe
echo ========================================================
echo.
pause
exit /b 0

:copy_error
echo.
echo [!] Ошибка при копировании файлов в папку release\!
pause
exit /b 1