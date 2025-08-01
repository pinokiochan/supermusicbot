#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мониторинг логов бота в реальном времени
"""

import os
import time
from datetime import datetime
import glob

def get_latest_log_file():
    """Получить последний файл лога"""
    log_files = glob.glob("logs/bot_*.log")
    if not log_files:
        return None
    return max(log_files, key=os.path.getctime)

def monitor_logs():
    """Мониторинг логов в реальном времени"""
    print("🔍 МОНИТОРИНГ ЛОГОВ MUSIC BOT")
    print("=" * 70)
    print("Нажмите Ctrl+C для выхода")
    print("=" * 70)
    
    log_file = get_latest_log_file()
    if not log_file:
        print("❌ Файлы логов не найдены")
        return
    
    print(f"📝 Отслеживаем: {log_file}")
    print("=" * 70)
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # Переходим в конец файла
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    # Выделяем важные события
                    if "👤 USER:" in line:
                        print(f"🟢 {line.strip()}")
                    elif "🆕 NEW USER:" in line:
                        print(f"🔥 {line.strip()}")
                    elif "❌" in line or "ERROR" in line:
                        print(f"🔴 {line.strip()}")
                    elif "✅" in line:
                        print(f"🟢 {line.strip()}")
                    elif "🔍 NEW SEARCH:" in line:
                        print(f"🔵 {line.strip()}")
                    elif "🔄 CACHE HIT:" in line:
                        print(f"🟡 {line.strip()}")
                    else:
                        print(line.strip())
                else:
                    time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n👋 Мониторинг остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    monitor_logs()
