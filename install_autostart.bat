@echo off
title Установка автозапуска Music Bot
echo ========================================
echo    УСТАНОВКА АВТОЗАПУСКА MUSIC BOT
echo ========================================
echo.

REM Получаем путь к текущей папке
set "CURRENT_DIR=%~dp0"
set "BAT_FILE=%CURRENT_DIR%start_bot.bat"

echo Текущая папка: %CURRENT_DIR%
echo Файл запуска: %BAT_FILE%
echo.

REM Проверяем существование файла запуска
if not exist "%BAT_FILE%" (
    echo ❌ ОШИБКА: Файл start_bot.bat не найден!
    echo Убедитесь, что файл находится в той же папке.
    pause
    exit /b 1
)

echo ✅ Файл запуска найден
echo.

REM Создаем ярлык в автозагрузке
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\Music Bot.lnk"

echo Создание ярлыка в автозагрузке...
echo Папка автозагрузки: %STARTUP_FOLDER%

REM Используем PowerShell для создания ярлыка
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%BAT_FILE%'; $Shortcut.WorkingDirectory = '%CURRENT_DIR%'; $Shortcut.Description = 'Music Bot Telegram'; $Shortcut.Save()"

if exist "%SHORTCUT_PATH%" (
    echo ✅ Ярлык успешно создан!
    echo.
    echo 🎉 АВТОЗАПУСК НАСТРОЕН!
    echo.
    echo Теперь бот будет автоматически запускаться при включении компьютера.
    echo.
    echo 📁 Расположение ярлыка: %SHORTCUT_PATH%
    echo 📝 Логи будут сохраняться в папку: %CURRENT_DIR%logs\
    echo.
    echo Хотите запустить бота сейчас? (y/n)
    set /p choice=
    if /i "%choice%"=="y" (
        echo Запуск бота...
        start "" "%BAT_FILE%"
    )
) else (
    echo ❌ ОШИБКА: Не удалось создать ярлык
    echo Попробуйте запустить от имени администратора
)

echo.
pause
@echo off
title Установка автозапуска Music Bot
echo ========================================
echo    УСТАНОВКА АВТОЗАПУСКА MUSIC BOT
echo ========================================
echo.

REM Получаем путь к текущей папке
set "CURRENT_DIR=%~dp0"
set "BAT_FILE=%CURRENT_DIR%start_bot.bat"

echo Текущая папка: %CURRENT_DIR%
echo Файл запуска: %BAT_FILE%
echo.

REM Проверяем существование файла запуска
if not exist "%BAT_FILE%" (
    echo ❌ ОШИБКА: Файл start_bot.bat не найден!
    echo Убедитесь, что файл находится в той же папке.
    pause
    exit /b 1
)

echo ✅ Файл запуска найден
echo.

REM Создаем ярлык в автозагрузке
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\Music Bot.lnk"

echo Создание ярлыка в автозагрузке...
echo Папка автозагрузки: %STARTUP_FOLDER%

REM Используем PowerShell для создания ярлыка
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%BAT_FILE%'; $Shortcut.WorkingDirectory = '%CURRENT_DIR%'; $Shortcut.Description = 'Music Bot Telegram'; $Shortcut.Save()"

if exist "%SHORTCUT_PATH%" (
    echo ✅ Ярлык успешно создан!
    echo.
    echo 🎉 АВТОЗАПУСК НАСТРОЕН!
    echo.
    echo Теперь бот будет автоматически запускаться при включении компьютера.
    echo.
    echo 📁 Расположение ярлыка: %SHORTCUT_PATH%
    echo 📝 Логи будут сохраняться в папку: %CURRENT_DIR%logs\
    echo.
    echo Хотите запустить бота сейчас? (y/n)
    set /p choice=
    if /i "%choice%"=="y" (
        echo Запуск бота...
        start "" "%BAT_FILE%"
    )
) else (
    echo ❌ ОШИБКА: Не удалось создать ярлык
    echo Попробуйте запустить от имени администратора
)

echo.
pause
