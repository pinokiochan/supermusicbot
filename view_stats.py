#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Просмотр статистики и пользователей бота
"""

import json
import os
from datetime import datetime
from collections import Counter

USERS_FILE = "data/users.json"
STATS_FILE = "data/stats.json"

def load_data(filename):
    """Загрузка данных из файла"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки {filename}: {e}")
    return {}

def format_datetime(iso_string):
    """Форматирование даты и времени"""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime("%d.%m.%Y %H:%M:%S")
    except:
        return iso_string

def show_general_stats():
    """Показать общую статистику"""
    stats = load_data(STATS_FILE)
    users = load_data(USERS_FILE)
    
    print("=" * 70)
    print("📊 ОБЩАЯ СТАТИСТИКА MUSIC BOT")
    print("=" * 70)
    print(f"👥 Всего пользователей: {len(users)}")
    print(f"🔍 Всего поисков: {stats.get('total_searches', 0)}")
    print(f"📥 Всего скачиваний: {stats.get('total_downloads', 0)}")
    print(f"📜 Запросов текстов: {stats.get('total_lyrics', 0)}")
    
    if 'bot_started' in stats:
        print(f"🚀 Бот запущен: {format_datetime(stats['bot_started'])}")
    
    print("=" * 70)

def show_users_list():
    """Показать список пользователей"""
    users = load_data(USERS_FILE)
    
    if not users:
        print("❌ Пользователи не найдены")
        return
    
    print("=" * 90)
    print("👥 СПИСОК ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 90)
    
    for user_id, user_data in users.items():
        username = f"@{user_data.get('username', 'N/A')}" if user_data.get('username') else "Без username"
        full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '') or ''}".strip()
        first_seen = format_datetime(user_data.get('first_seen', ''))
        last_seen = format_datetime(user_data.get('last_seen', ''))
        total_actions = user_data.get('total_actions', len(user_data.get('actions', [])))
        
        print(f"🆔 ID: {user_id}")
        print(f"👤 Имя: {full_name}")
        print(f"📱 Username: {username}")
        print(f"📅 Первый визит: {first_seen}")
        print(f"🕐 Последний визит: {last_seen}")
        print(f"⚡ Всего действий: {total_actions}")
        print("-" * 90)

def show_user_details(user_id):
    """Показать детали конкретного пользователя"""
    users = load_data(USERS_FILE)
    
    if user_id not in users:
        print(f"❌ Пользователь с ID {user_id} не найден")
        return
    
    user_data = users[user_id]
    username = f"@{user_data.get('username', 'N/A')}" if user_data.get('username') else "Без username"
    full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '') or ''}".strip()
    
    print("=" * 90)
    print(f"👤 ДЕТАЛИ ПОЛЬЗОВАТЕЛЯ: {full_name} ({username})")
    print("=" * 90)
    print(f"🆔 ID: {user_id}")
    print(f"👤 Имя: {full_name}")
    print(f"📱 Username: {username}")
    print(f"📅 Первый визит: {format_datetime(user_data.get('first_seen', ''))}")
    print(f"🕐 Последний визит: {format_datetime(user_data.get('last_seen', ''))}")
    print(f"⚡ Всего действий: {user_data.get('total_actions', 0)}")
    print()
    
    actions = user_data.get('actions', [])
    if actions:
        print(f"⚡ ПОСЛЕДНИЕ {min(20, len(actions))} ДЕЙСТВИЙ:")
        print("-" * 90)
        
        # Показываем последние 20 действий
        for action in actions[-20:]:
            timestamp = format_datetime(action.get('timestamp', ''))
            action_type = action.get('action', 'unknown')
            details = action.get('details', '')
            
            print(f"🕐 {timestamp} | {action_type.upper()}: {details}")
        
        # Статистика действий
        action_counts = Counter(action['action'] for action in actions)
        print()
        print("📊 СТАТИСТИКА ДЕЙСТВИЙ:")
        print("-" * 50)
        for action_type, count in action_counts.most_common():
            print(f"{action_type}: {count}")
    else:
        print("❌ Действий не найдено")

def show_top_users():
    """Показать топ активных пользователей"""
    users = load_data(USERS_FILE)
    
    if not users:
        print("❌ Пользователи не найдены")
        return
    
    # Сортируем по количеству действий
    sorted_users = sorted(
        users.items(),
        key=lambda x: x[1].get('total_actions', len(x[1].get('actions', []))),
        reverse=True
    )
    
    print("=" * 90)
    print("🏆 ТОП-10 АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 90)
    
    for i, (user_id, user_data) in enumerate(sorted_users[:10], 1):
        username = f"@{user_data.get('username', 'N/A')}" if user_data.get('username') else "Без username"
        full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '') or ''}".strip()
        total_actions = user_data.get('total_actions', len(user_data.get('actions', [])))
        
        print(f"{i:2d}. {full_name} ({username}) - {total_actions} действий")

def main():
    """Главное меню"""
    while True:
        print("\n" + "=" * 70)
        print("🎵 СТАТИСТИКА MUSIC BOT")
        print("=" * 70)
        print("1. 📊 Общая статистика")
        print("2. 👥 Список всех пользователей")
        print("3. 🔍 Детали пользователя")
        print("4. 🏆 Топ активных пользователей")
        print("5. 🚪 Выход")
        print("=" * 70)
        
        choice = input("Выберите опцию (1-5): ").strip()
        
        if choice == "1":
            show_general_stats()
        elif choice == "2":
            show_users_list()
        elif choice == "3":
            user_id = input("Введите ID пользователя: ").strip()
            show_user_details(user_id)
        elif choice == "4":
            show_top_users()
        elif choice == "5":
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор. Попробуйте снова.")
        
        input("\nНажмите Enter для продолжения...")

if __name__ == "__main__":
    main()
