@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo    Сборка FS-XML.exe из launcher.cs
echo ========================================================
echo.

if not exist "launcher.cs" (
    echo [!] Не найден файл launcher.cs!
    pause
    exit /b 1
)

if not exist "python" (
    echo [!] Не найдена папка python!
    pause
    exit /b 1
)

:: 1. Поиск компилятора C# (csc.exe из .NET Framework 4.x)
set "CSC_PATH="
if exist "%SystemRoot%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" (
    set "CSC_PATH=%SystemRoot%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
) else if exist "%SystemRoot%\Microsoft.NET\Framework\v4.0.30319\csc.exe" (
    set "CSC_PATH=%SystemRoot%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
)

if not defined CSC_PATH (
    for /f "delims=" %%I in ('where csc.exe 2^>nul') do (
        set "CSC_PATH=%%I"
        goto :csc_found
    )
)

:csc_found
if not defined CSC_PATH (
    echo [!] Не найден компилятор csc.exe ^(.NET Framework 4.x^).
    pause
    exit /b 1
)
echo [+] Компилятор: %CSC_PATH%

:: 2. Определение разрядности python3XX.dll (x64 или x86)
set "PLATFORM=x64"
for /f "usebackq delims=" %%A in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$dll = Get-ChildItem -Path 'python' -Filter 'python3*.dll' | Where-Object { $_.Name -match '^python3\d+\.dll$' } | Select-Object -First 1; if (-not $dll) { Write-Output 'x64'; exit 0 }; $fs = [System.IO.File]::OpenRead($dll.FullName); $br = New-Object System.IO.BinaryReader($fs); $fs.Seek(0x3C, 'Begin') | Out-Null; $pe = $br.ReadInt32(); $fs.Seek($pe + 4, 'Begin') | Out-Null; $machine = $br.ReadUInt16(); $br.Close(); $fs.Close(); if ($machine -eq 0x014c) { Write-Output 'x86' } else { Write-Output 'x64' }"`) do (
    set "PLATFORM=%%A"
)
echo [+] Целевая платформа ^(по Python DLL^): %PLATFORM%

:: 3. Проверка иконки
set "ICON_ARG="
if exist "images\FS-XML.ico" (
    set "ICON_ARG=/win32icon:images\FS-XML.ico"
    echo [+] Иконка: images\FS-XML.ico
) else (
    echo [!] Внимание: файл images\FS-XML.ico не найден, сборка пройдет без иконки.
)

echo.
echo [i] Компиляция FS-XML.exe...
"%CSC_PATH%" /nologo /optimize+ /target:winexe /platform:%PLATFORM% %ICON_ARG% /reference:System.Windows.Forms.dll /out:FS-XML.exe launcher.cs
if errorlevel 1 (
    echo.
    echo [!] Ошибка компиляции FS-XML.exe!
    pause
    exit /b 1
)

echo.
echo ========================================================
echo    Готово! Собран файл FS-XML.exe
echo ========================================================
echo.
pause