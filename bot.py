import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, InlineQueryHandler, ContextTypes
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.constants import ParseMode
import asyncio
from aiohttp import web
import threading

from config import BOT_TOKEN
from utils.ytsearch import search_youtube_multiple, search_youtube, save_user_search, get_smart_recommendations
from utils.downloader import download_audio
from utils.lyrics import get_lyrics
from utils.recommender import store_artist, get_recommendations
from uuid import uuid4
import time

# Простой кэш для результатов поиска
search_cache = {}
CACHE_TIMEOUT = 300  # 5 минут

def get_cached_search(query, count=6):
    """Получение результатов из кэша или новый поиск"""
    cache_key = f"{query}_{count}"
    current_time = time.time()
    
    if cache_key in search_cache:
        cached_data, timestamp = search_cache[cache_key]
        if current_time - timestamp < CACHE_TIMEOUT:
            return cached_data
    
    # Новый поиск
    results = search_youtube_multiple(query, count)
    search_cache[cache_key] = (results, current_time)
    
    # Очищаем старый кэш
    if len(search_cache) > 50:
        oldest_key = min(search_cache.keys(), key=lambda k: search_cache[k][1])
        del search_cache[oldest_key]
    
    return results

# Хранение результатов поиска для пользователей
user_search_results = {}
user_modes = {}

# Веб-сервер для health checks
async def health_check(request):
    return web.Response(text="🎵 Music Bot is running! ✅", status=200)

async def status_check(request):
    return web.Response(text="OK", status=200)

def start_web_server():
    """Запуск веб-сервера в отдельном потоке"""
    async def create_app():
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        app.router.add_get('/status', status_check)
        
        port = int(os.environ.get('PORT', 10000))
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        print(f"🌐 Web server started on port {port}")
        
        # Держим сервер запущенным
        while True:
            await asyncio.sleep(3600)  # Спим час
    
    def run_server():
        asyncio.run(create_app())
    
    # Запускаем в отдельном потоке
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовое сообщение с улучшенным дизайном"""
    welcome_text = """
🎵 <b>Добро пожаловать в Music Search Bot!</b> 🎵

🔥 <i>Твой персональный музыкальный ассистент</i>

<b>✨ Новые возможности:</b>
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
    
    user_id = query.from_user.id
    
    if query.data == "search_song":
        user_modes[user_id] = "search_song"
        await query.message.reply_text(
            "🔍 <b>Режим поиска песен активирован!</b>\n\n"
            "Напиши название песни, и я найду несколько вариантов для выбора 🎵",
            parse_mode=ParseMode.HTML
        )
    
    elif query.data == "search_artist":
        user_modes[user_id] = "search_artist"
        await query.message.reply_text(
            "🎭 <b>Поиск по артисту активирован!</b>\n\n"
            "Напиши имя артиста, и я найду его популярные песни 🌟",
            parse_mode=ParseMode.HTML
        )
    
    elif query.data == "get_lyrics":
        user_modes[user_id] = "lyrics"
        await query.message.reply_text(
            "📜 <b>Режим получения текстов активирован!</b>\n\n"
            "Напиши название песни для получения текста 🎤",
            parse_mode=ParseMode.HTML
        )
    
    elif query.data == "recommend":
        await show_recommendations(query.message, user_id)
    
    elif query.data.startswith("download_"):
        await handle_download(query, user_id)
    
    elif query.data.startswith("lyrics_"):
        await handle_lyrics_from_search(query, user_id)

async def show_recommendations(message, user_id):
    """Показ рекомендаций - минимум 5 песен"""
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
    
    # Сохраняем рекомендации как результаты поиска
    user_search_results[user_id] = recs
    
    text = "🎯 <b>Рекомендации специально для тебя:</b>\n\n"
    keyboard = []
    
    for i, rec in enumerate(recs[:6]):
        text += f"🎵 <b>{i+1}.</b> {rec['title']}\n"
        text += f"⏱ {rec['duration']} | 👤 {rec['uploader']}\n\n"
        
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

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    mode = user_modes.get(user_id, "search_song")

    if mode == "lyrics":
        await handle_lyrics_search(update.message, text)
    elif mode == "search_artist":
        await handle_artist_search(update.message, text, user_id)
    else:
        await handle_song_search(update.message, text, user_id)

async def handle_song_search(message, query, user_id):
    """Быстрый поиск песен с кэшированием"""
    loading_msg = await message.reply_text(
        "🔍 <b>Быстрый поиск...</b> ⚡",
        parse_mode=ParseMode.HTML
    )
    
    # Используем кэш для ускорения
    results = get_cached_search(query, 6)
    
    await loading_msg.delete()
    
    if not results:
        await message.reply_text(
            f"❌ <b>Ничего не найдено:</b> <i>{query}</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    user_search_results[user_id] = results
    
    # Упрощенный вывод для скорости
    text = f"🎵 <b>Найдено {len(results)} песен:</b> <i>{query}</i>\n\n"
    keyboard = []
    
    for i, result in enumerate(results):
        text += f"🎶 <b>{i+1}.</b> {result['title']}\n"
        text += f"👤 {result['uploader']}\n\n"
        
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

async def handle_artist_search(message, artist_name, user_id):
    """Быстрый поиск по артисту"""
    loading_msg = await message.reply_text(
        f"🎭 <b>Быстрый поиск артиста...</b> ⚡",
        parse_mode=ParseMode.HTML
    )
    
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
        text += f"🎶 <b>{i+1}.</b> {result['title']}\n\n"
        
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

async def handle_lyrics_search(message, query):
    loading_msg = await message.reply_text(
        f"📜 <b>Ищу текст песни:</b> <i>{query}</i>\n⏳ Подождите...",
        parse_mode=ParseMode.HTML
    )
    
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

async def handle_download(query, user_id):
    try:
        index = int(query.data.split("_")[1])
        
        if user_id not in user_search_results or index >= len(user_search_results[user_id]):
            await query.message.reply_text("❌ Ошибка: песня не найдена")
            return
        
        selected_song = user_search_results[user_id][index]
        save_user_search(user_id, "download", selected_song)
        
        loading_msg = await query.message.reply_text(
            f"📥 <b>Скачиваю:</b> <i>{selected_song['title']}</i>\n⏳ Подождите...",
            parse_mode=ParseMode.HTML
        )
        
        audio_path = download_audio(selected_song['url'])
        
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, 'rb') as audio_file:
                await query.message.reply_audio(
                    audio=audio_file,
                    title=selected_song['title'],
                    caption=f"🎵 <b>{selected_song['title']}</b>",
                    parse_mode=ParseMode.HTML
                )
            os.remove(audio_path)
            await loading_msg.delete()
        else:
            await loading_msg.edit_text(
                f"❌ <b>Ошибка при скачивании:</b> <i>{selected_song['title']}</i>",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        await query.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

async def handle_lyrics_from_search(query, user_id):
    try:
        index = int(query.data.split("_")[1])
        
        if user_id not in user_search_results or index >= len(user_search_results[user_id]):
            await query.message.reply_text("❌ Ошибка: песня не найдена")
            return
        
        selected_song = user_search_results[user_id][index]
        
        loading_msg = await query.message.reply_text(
            f"📜 <b>Получаю текст:</b> <i>{selected_song['title']}</i>\n⏳ Подождите...",
            parse_mode=ParseMode.HTML
        )
        
        lyrics = get_lyrics(selected_song['title'])
        await loading_msg.delete()
        
        if lyrics:
            if len(lyrics) > 4000:
                parts = [lyrics[i:i+4000] for i in range(0, len(lyrics), 4000)]
                for i, part in enumerate(parts):
                    header = f"📜 <b>{selected_song['title']}</b> (часть {i+1}/{len(parts)}):\n\n" if i == 0 else ""
                    await query.message.reply_text(f"{header}<pre>{part}</pre>", parse_mode=ParseMode.HTML)
            else:
                await query.message.reply_text(
                    f"📜 <b>{selected_song['title']}</b>\n\n<pre>{lyrics}</pre>",
                    parse_mode=ParseMode.HTML
                )
        else:
            await query.message.reply_text(
                f"❌ <b>Не удалось найти текст для:</b> <i>{selected_song['title']}</i>",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        await query.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
    
    results_list = search_youtube_multiple(query, 5)
    inline_results = []
    
    for result in results_list:
        inline_results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=result['title'],
                input_message_content=InputTextMessageContent(result['title']),
                description=f"⏱ {result['duration']} | 👤 {result['uploader']}",
            )
        )
    
    await update.inline_query.answer(inline_results)

if __name__ == "__main__":
    # Создаем папку для загрузок
    os.makedirs("downloads", exist_ok=True)
    
    # Запускаем веб-сервер для health checks
    start_web_server()
    
    # Создаем приложение бота
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(InlineQueryHandler(inline_handler))

    print("🎵 Music Bot запущен на Render!")
    print("✨ Функции:")
    print("   • Множественный выбор из 5+ песен")
    print("   • Поиск по артисту")
    print("   • Улучшенные рекомендации")
    print("   • Health check сервер на порту", os.environ.get('PORT', 10000))
    
    # Запускаем бота
    app.run_polling()
