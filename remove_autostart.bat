@echo off
title Удаление автозапуска Music Bot
echo ========================================
echo    УДАЛЕНИЕ АВТОЗАПУСКА MUSIC BOT
echo ========================================
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\Music Bot.lnk"

echo Поиск ярлыка автозапуска...
echo Путь: %SHORTCUT_PATH%
echo.

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo ✅ Ярлык автозапуска удален!
    echo Бот больше не будет запускаться автоматически.
) else (
    echo ⚠️ Ярлык автозапуска не найден
    echo Возможно, он уже был удален ранее.
)

echo.
pause
