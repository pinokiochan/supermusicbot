import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, InlineQueryHandler, ContextTypes
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.constants import ParseMode
from config import BOT_TOKEN
from utils.ytsearch import search_youtube_multiple, search_youtube, save_user_search, get_smart_recommendations
from utils.downloader import download_audio
from utils.lyrics import get_lyrics
from utils.recommender import store_artist, get_recommendations
from uuid import uuid4
import time
from functools import lru_cache
import json

# Создаем папки для логов и данных
os.makedirs("logs", exist_ok=True)
os.makedirs("downloads", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Настройка логирования
log_filename = f'logs/bot_{datetime.now().strftime("%Y-%m-%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Файлы для хранения данных
USERS_FILE = "data/users.json"
STATS_FILE = "data/stats.json"

def load_json_file(filename, default=None):
    """Универсальная загрузка JSON файлов"""
    if default is None:
        default = {}
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки {filename}: {e}")
    return default

def save_json_file(filename, data):
    """Универсальное сохранение JSON файлов"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения {filename}: {e}")

def load_users():
    """Загрузка данных пользователей"""
    return load_json_file(USERS_FILE, {})

def save_users(users_data):
    """Сохранение данных пользователей"""
    save_json_file(USERS_FILE, users_data)

def load_stats():
    """Загрузка статистики"""
    return load_json_file(STATS_FILE, {
        "total_users": 0, 
        "total_searches": 0, 
        "total_downloads": 0,
        "total_lyrics": 0,
        "bot_started": datetime.now().isoformat()
    })

def save_stats(stats_data):
    """Сохранение статистики"""
    save_json_file(STATS_FILE, stats_data)

def log_user_action(user, action, details=""):
    """Расширенное логирование действий пользователя"""
    user_info = f"@{user.username}" if user.username else f"ID:{user.id}"
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    
    # Основной лог
    logger.info(f"👤 USER: {user_info} ({full_name}) | ACTION: {action} | DETAILS: {details}")
    
    # Обновляем данные пользователя
    users_data = load_users()
    user_key = str(user.id)
    current_time = datetime.now().isoformat()
    
    if user_key not in users_data:
        users_data[user_key] = {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "first_seen": current_time,
            "actions": [],
            "total_actions": 0
        }
        
        # Увеличиваем счетчик новых пользователей
        stats = load_stats()
        stats["total_users"] += 1
        save_stats(stats)
        
        logger.info(f"🆕 NEW USER: {user_info} ({full_name})")
    
    # Обновляем информацию пользователя
    users_data[user_key]["last_seen"] = current_time
    users_data[user_key]["username"] = user.username  # Обновляем username
    users_data[user_key]["actions"].append({
        "action": action,
        "details": details,
        "timestamp": current_time
    })
    users_data[user_key]["total_actions"] += 1
    
    # Ограничиваем историю действий (последние 100)
    if len(users_data[user_key]["actions"]) > 100:
        users_data[user_key]["actions"] = users_data[user_key]["actions"][-100:]
    
    # Обновляем общую статистику
    stats = load_stats()
    if action == "search":
        stats["total_searches"] += 1
    elif action == "download":
        stats["total_downloads"] += 1
    elif action == "lyrics_request":
        stats["total_lyrics"] += 1
    
    save_stats(stats)
    save_users(users_data)

# Кэш для поиска
search_cache = {}
CACHE_TIMEOUT = 300  # 5 минут

def get_cached_search(query, count=6):
    """Получение результатов из кэша или новый поиск"""
    cache_key = f"{query}_{count}"
    current_time = time.time()
    
    if cache_key in search_cache:
        cached_data, timestamp = search_cache[cache_key]
        if current_time - timestamp < CACHE_TIMEOUT:
            logger.info(f"🔄 CACHE HIT: {query}")
            return cached_data
    
    # Новый поиск
    logger.info(f"🔍 NEW SEARCH: {query}")
    try:
        results = search_youtube_multiple(query, count)
        search_cache[cache_key] = (results, current_time)
        
        # Очищаем старый кэш
        if len(search_cache) > 50:
            oldest_key = min(search_cache.keys(), key=lambda k: search_cache[k][1])
            del search_cache[oldest_key]
        
        return results
    except Exception as e:
        logger.error(f"Search error for '{query}': {e}")
        return []

# Хранение результатов поиска для пользователей
user_search_results = {}
user_modes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовое сообщение с логированием"""
    user = update.effective_user
    log_user_action(user, "start", "Bot started")
    
    welcome_text = """🎵 <b>Добро пожаловать в Music Search Bot!</b> 🎵

🔥 <i>Твой персональный музыкальный ассистент</i>

<b>✨ Возможности:</b>
🎯 Поиск с выбором из 5+ вариантов
🎭 Поиск по артисту
📜 Получение текстов песен
🎪 Умные рекомендации (5+ песен)
📥 Скачивание в MP3

<b>Просто напиши название песни или артиста!</b>
    """
    
    keyboard = [
        [
            InlineKeyboardButton("🔍 Поиск песни", callback_data="search_song"),
            InlineKeyboardButton("🎭 Поиск по артисту", callback_data="search_artist")
        ],
        [
            InlineKeyboardButton("📜 Получить текст", callback_data="get_lyrics"),
            InlineKeyboardButton("🎵 Рекомендации", callback_data="recommend")
        ]
    ]
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    
    if query.data == "search_song":
        user_modes[user_id] = "search_song"
        log_user_action(user, "mode_change", "search_song")
        await query.message.reply_text(
            "🔍 <b>Режим поиска песен активирован!</b>\n\n"
            "Напиши название песни, и я найду несколько вариантов для выбора 🎵",
            parse_mode=ParseMode.HTML
        )
    
    elif query.data == "search_artist":
        user_modes[user_id] = "search_artist"
        log_user_action(user, "mode_change", "search_artist")
        await query.message.reply_text(
            "🎭 <b>Поиск по артисту активирован!</b>\n\n"
            "Напиши имя артиста, и я найду его популярные песни 🌟",
            parse_mode=ParseMode.HTML
        )
    
    elif query.data == "get_lyrics":
        user_modes[user_id] = "lyrics"
        log_user_action(user, "mode_change", "lyrics")
        await query.message.reply_text(
            "📜 <b>Режим получения текстов активирован!</b>\n\n"
            "Напиши название песни для получения текста 🎤",
            parse_mode=ParseMode.HTML
        )
    
    elif query.data == "recommend":
        log_user_action(user, "button_click", "recommendations")
        await show_recommendations(query.message, user_id)
    
    elif query.data.startswith("download_"):
        await handle_download(query, user_id)
    
    elif query.data.startswith("lyrics_"):
        await handle_lyrics_from_search(query, user_id)

async def show_recommendations(message, user_id):
    """Показ рекомендаций"""
    try:
        recs = get_recommendations(user_id)
        
        if not recs:
            keyboard = [[InlineKeyboardButton("🔍 Начать поиск", callback_data="search_song")]]
            await message.reply_text(
                "🤔 <b>Пока нет рекомендаций!</b>\n\n"
                "Сначала найди несколько песен, чтобы я мог предложить что-то интересное! 🎵",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            return
        
        user_search_results[user_id] = recs
        
        text = "🎯 <b>Рекомендации специально для тебя:</b>\n\n"
        keyboard = []
        
        for i, rec in enumerate(recs[:6]):
            text += f"🎵 <b>{i+1}.</b> {rec['title']}\n"
            text += f"⏱ {rec.get('duration', 'N/A')} | 👤 {rec.get('uploader', 'N/A')}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"📥 Скачать #{i+1}", callback_data=f"download_{i}"),
                InlineKeyboardButton(f"📜 Текст #{i+1}", callback_data=f"lyrics_{i}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="recommend")])
        
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Recommendations error: {e}")
        await message.reply_text("❌ Ошибка при получении рекомендаций")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = update.message.text
    mode = user_modes.get(user_id, "search_song")
    
    try:
        if mode == "lyrics":
            log_user_action(user, "search", f"lyrics: {text}")
            await handle_lyrics_search(update.message, text)
        elif mode == "search_artist":
            log_user_action(user, "search", f"artist: {text}")
            await handle_artist_search(update.message, text, user_id)
        else:
            log_user_action(user, "search", f"song: {text}")
            await handle_song_search(update.message, text, user_id)
    except Exception as e:
        logger.error(f"Text handler error: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке запроса")

async def handle_song_search(message, query, user_id):
    """Поиск песен с кэшированием"""
    loading_msg = await message.reply_text(
        "🔍 <b>Быстрый поиск...</b> ⚡",
        parse_mode=ParseMode.HTML
    )
    
    try:
        results = get_cached_search(query, 6)
        await loading_msg.delete()
        
        if not results:
            await message.reply_text(
                f"❌ <b>Ничего не найдено:</b> <i>{query}</i>",
                parse_mode=ParseMode.HTML
            )
            return
        
        user_search_results[user_id] = results
        
        text = f"🎵 <b>Найдено {len(results)} песен:</b> <i>{query}</i>\n\n"
        keyboard = []
        
        for i, result in enumerate(results):
            text += f"🎶 <b>{i+1}.</b> {result.get('title', 'N/A')}\n"
            text += f"👤 {result.get('uploader', 'N/A')}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"📥 #{i+1}", callback_data=f"download_{i}"),
                InlineKeyboardButton(f"📜 #{i+1}", callback_data=f"lyrics_{i}")
            ])
        
        keyboard.append([InlineKeyboardButton("🎯 Рекомендации", callback_data="recommend")])
        
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Song search error: {e}")
        await loading_msg.edit_text("❌ Ошибка при поиске песен")

async def handle_artist_search(message, artist_name, user_id):
    """Поиск по артисту"""
    loading_msg = await message.reply_text(
        f"🎭 <b>Быстрый поиск артиста...</b> ⚡",
        parse_mode=ParseMode.HTML
    )
    
    try:
        store_artist(user_id, artist_name)
        results = get_cached_search(f"{artist_name} songs", 6)
        
        await loading_msg.delete()
        
        if not results:
            await message.reply_text(
                f"❌ <b>Артист не найден:</b> <i>{artist_name}</i>",
                parse_mode=ParseMode.HTML
            )
            return
        
        user_search_results[user_id] = results
        
        text = f"🎭 <b>Песни артиста:</b> <i>{artist_name}</i>\n\n"
        keyboard = []
        
        for i, result in enumerate(results):
            text += f"🎶 <b>{i+1}.</b> {result.get('title', 'N/A')}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"📥 #{i+1}", callback_data=f"download_{i}"),
                InlineKeyboardButton(f"📜 #{i+1}", callback_data=f"lyrics_{i}")
            ])
        
        keyboard.append([InlineKeyboardButton("🎯 Рекомендации", callback_data="recommend")])
        
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Artist search error: {e}")
        await loading_msg.edit_text("❌ Ошибка при поиске артиста")

async def handle_lyrics_search(message, query):
    """Поиск текстов песен"""
    loading_msg = await message.reply_text(
        f"📜 <b>Ищу текст песни:</b> <i>{query}</i>\n⏳ Подождите...",
        parse_mode=ParseMode.HTML
    )
    
    try:
        lyrics = get_lyrics(query)
        await loading_msg.delete()
        
        if lyrics:
            if len(lyrics) > 4000:
                parts = [lyrics[i:i+4000] for i in range(0, len(lyrics), 4000)]
                for i, part in enumerate(parts):
                    header = f"📜 <b>Текст песни</b> (часть {i+1}/{len(parts)}):\n\n" if i == 0 else ""
                    await message.reply_text(f"{header}<pre>{part}</pre>", parse_mode=ParseMode.HTML)
            else:
                await message.reply_text(f"📜 <b>Текст песни:</b>\n\n<pre>{lyrics}</pre>", parse_mode=ParseMode.HTML)
        else:
            await message.reply_text(
                f"❌ <b>Не удалось найти текст для:</b> <i>{query}</i>",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Lyrics search error: {e}")
        await loading_msg.edit_text("❌ Ошибка при поиске текста")

async def handle_download(query, user_id):
    """Обработка скачивания"""
    try:
        user = query.from_user
        index = int(query.data.split("_")[1])
        
        if user_id not in user_search_results or index >= len(user_search_results[user_id]):
            await query.message.reply_text("❌ Ошибка: песня не найдена")
            return
        
        selected_song = user_search_results[user_id][index]
        log_user_action(user, "download", selected_song.get('title', 'Unknown'))
        save_user_search(user_id, "download", selected_song)
        
        loading_msg = await query.message.reply_text(
            f"📥 <b>Скачиваю:</b> <i>{selected_song.get('title', 'Unknown')}</i>\n⏳ Подождите...",
            parse_mode=ParseMode.HTML
        )
        
        audio_path = download_audio(selected_song.get('url', ''))
        
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, 'rb') as audio_file:
                await query.message.reply_audio(
                    audio=audio_file,
                    title=selected_song.get('title', 'Unknown'),
                    caption=f"🎵 <b>{selected_song.get('title', 'Unknown')}</b>",
                    parse_mode=ParseMode.HTML
                )
            os.remove(audio_path)
            await loading_msg.delete()
            logger.info(f"✅ DOWNLOAD SUCCESS: {selected_song.get('title')} for user {user.username or user.id}")
        else:
            await loading_msg.edit_text(
                f"❌ <b>Ошибка при скачивании:</b> <i>{selected_song.get('title', 'Unknown')}</i>",
                parse_mode=ParseMode.HTML
            )
            logger.error(f"❌ DOWNLOAD FAILED: {selected_song.get('title')} for user {user.username or user.id}")
    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

async def handle_lyrics_from_search(query, user_id):
    """Получение текста из результатов поиска"""
    try:
        user = query.from_user
        index = int(query.data.split("_")[1])
        
        if user_id not in user_search_results or index >= len(user_search_results[user_id]):
            await query.message.reply_text("❌ Ошибка: песня не найдена")
            return
        
        selected_song = user_search_results[user_id][index]
        log_user_action(user, "lyrics_request", selected_song.get('title', 'Unknown'))
        
        loading_msg = await query.message.reply_text(
            f"📜 <b>Получаю текст:</b> <i>{selected_song.get('title', 'Unknown')}</i>\n⏳ Подождите...",
            parse_mode=ParseMode.HTML
        )
        
        lyrics = get_lyrics(selected_song.get('title', ''))
        await loading_msg.delete()
        
        if lyrics:
            if len(lyrics) > 4000:
                parts = [lyrics[i:i+4000] for i in range(0, len(lyrics), 4000)]
                for i, part in enumerate(parts):
                    header = f"📜 <b>{selected_song.get('title', 'Unknown')}</b> (часть {i+1}/{len(parts)}):\n\n" if i == 0 else ""
                    await query.message.reply_text(f"{header}<pre>{part}</pre>", parse_mode=ParseMode.HTML)
            else:
                await query.message.reply_text(
                    f"📜 <b>{selected_song.get('title', 'Unknown')}</b>\n\n<pre>{lyrics}</pre>",
                    parse_mode=ParseMode.HTML
                )
            logger.info(f"✅ LYRICS SUCCESS: {selected_song.get('title')} for user {user.username or user.id}")
        else:
            await query.message.reply_text(
                f"❌ <b>Не удалось найти текст для:</b> <i>{selected_song.get('title', 'Unknown')}</i>",
                parse_mode=ParseMode.HTML
            )
            logger.warning(f"⚠️ LYRICS NOT FOUND: {selected_song.get('title')} for user {user.username or user.id}")
    except Exception as e:
        logger.error(f"Lyrics error: {e}")
        await query.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка inline запросов"""
    query = update.inline_query.query
    user = update.effective_user
    
    if not query:
        return
    
    try:
        log_user_action(user, "inline_search", query)
        results_list = search_youtube_multiple(query, 5)
        inline_results = []
        
        for result in results_list:
            inline_results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=result.get('title', 'Unknown'),
                    input_message_content=InputTextMessageContent(result.get('title', 'Unknown')),
                    description=f"⏱ {result.get('duration', 'N/A')} | 👤 {result.get('uploader', 'N/A')}",
                )
            )
        
        await update.inline_query.answer(inline_results)
    except Exception as e:
        logger.error(f"Inline handler error: {e}")

def print_startup_info():
    """Информация о запуске с статистикой"""
    stats = load_stats()
    users_count = len(load_users())
    
    print("=" * 70)
    print("🎵 ENHANCED MUSIC BOT ЗАПУЩЕН!")
    print("=" * 70)
    print("✨ Возможности:")
    print("   • Множественный выбор из 5+ песен")
    print("   • Поиск по артисту")
    print("   • Улучшенные рекомендации")
    print("   • Красивый интерфейс")
    print("   • Полное логирование")
    print("   • Мониторинг пользователей")
    print("   • Кэширование запросов")
    print("=" * 70)
    print("📊 ТЕКУЩАЯ СТАТИСТИКА:")
    print(f"   👥 Всего пользователей: {users_count}")
    print(f"   🔍 Всего поисков: {stats.get('total_searches', 0)}")
    print(f"   📥 Всего скачиваний: {stats.get('total_downloads', 0)}")
    print(f"   📜 Запросов текстов: {stats.get('total_lyrics', 0)}")
    print("=" * 70)
    print(f"📝 Логи: {log_filename}")
    print(f"👥 Пользователи: {USERS_FILE}")
    print(f"📊 Статистика: {STATS_FILE}")
    print("=" * 70)

if __name__ == "__main__":
    try:
        
        print_startup_info()
        logger.info("🚀 Enhanced Music Bot starting...")
        
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
        app.add_handler(InlineQueryHandler(inline_handler))
        
        logger.info("✅ Bot handlers registered successfully")
        logger.info("🔄 Starting polling...")
        
        app.run_polling()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        print(f"❌ Критическая ошибка: {e}")
        input("Нажмите Enter для выхода...")
