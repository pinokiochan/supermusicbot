@echo off
chcp 65001 >nul
title Music Bot - Диагностика и запуск
echo ========================================
echo    MUSIC BOT - ПОИСК И ЗАПУСК
echo ========================================
echo.

echo 🔍 ПОИСК ФАЙЛА bot.py...
echo.

REM Вариант 1: Проверяем основной путь
echo Проверяем: C:\Users\Lenovo\Downloads\supermusicbot (1)\supermusicbot
if exist "C:\Users\Lenovo\Downloads\supermusicbot (1)\supermusicbot\bot.py" (
    cd /d "C:\Users\Lenovo\Downloads\supermusicbot (1)\supermusicbot"
    echo ✅ НАЙДЕН в основной папке!
    goto :found
)

REM Вариант 2: Ищем в Downloads
echo Проверяем папки в Downloads...
for /d %%i in ("C:\Users\Lenovo\Downloads\*supermusicbot*") do (
    if exist "%%i\bot.py" (
        cd /d "%%i"
        echo ✅ НАЙДЕН в: %%i
        goto :found
    )
    if exist "%%i\supermusicbot\bot.py" (
        cd /d "%%i\supermusicbot"
        echo ✅ НАЙДЕН в: %%i\supermusicbot
        goto :found
    )
)

REM Вариант 3: Ищем на рабочем столе
echo Проверяем рабочий стол...
for /d %%i in ("C:\Users\Lenovo\Desktop\*supermusicbot*") do (
    if exist "%%i\bot.py" (
        cd /d "%%i"
        echo ✅ НАЙДЕН на рабочем столе: %%i
        goto :found
    )
)

REM Вариант 4: Глобальный поиск
echo Выполняем глобальный поиск bot.py...
for /f "delims=" %%i in ('dir "C:\Users\Lenovo\bot.py" /s /b 2^>nul ^| findstr supermusicbot') do (
    set "botpath=%%i"
    for %%j in ("%%i") do set "botdir=%%~dpj"
    cd /d "!botdir!"
    echo ✅ НАЙДЕН при глобальном поиске: !botdir!
    goto :found
)

echo ❌ bot.py НЕ НАЙДЕН!
echo.
echo 📋 Показываем содержимое Downloads:
dir "C:\Users\Lenovo\Downloads" /b | findstr -i music
echo.
echo 🔧 РЕШЕНИЕ:
echo 1. Найдите папку с ботом вручную
echo 2. Скопируйте полный путь к папке
echo 3. Замените путь в этом файле
echo.
pause
exit /b 1

:found
echo.
echo 📁 Текущая папка: %CD%
echo.

REM Показываем содержимое папки
echo 📋 Содержимое папки:
dir /b
echo.

REM Проверяем наличие нужных файлов
if exist "bot.py" (
    echo ✅ bot.py найден
) else (
    echo ❌ bot.py НЕ найден
)

if exist "config.py" (
    echo ✅ config.py найден
) else (
    echo ❌ config.py НЕ найден
)

echo.

REM Создаем папки
if not exist "logs" (
    mkdir logs
    echo 📁 Создана папка logs
)

if not exist "data" (
    mkdir data
    echo 📁 Создана папка data
)

echo.
echo 🚀 ЗАПУСК БОТА...
echo.

python bot.py

if errorlevel 1 (
    echo.
    echo ❌ Бот завершился с ошибкой
    echo 📁 Папка: %CD%
    echo.
    echo 🔍 Проверьте:
    echo - Установлен ли Python
    echo - Правильный ли токен в config.py
    echo - Установлены ли зависимости (pip install -r requirements.txt)
    echo.
    pause
) else (
    echo.
    echo ✅ Бот завершился нормально
)