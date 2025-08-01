import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from aiohttp import web
import asyncio

from config import BOT_TOKEN
from utils.ytsearch import search_youtube_multiple, save_user_search
from utils.downloader import download_audio, cleanup_old_files
from utils.lyrics import get_lyrics
from utils.recommender import store_artist, get_recommendations
import time

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовое сообщение"""
    welcome_text = """
🎵 <b>Добро пожаловать в Music Search Bot!</b> 🎵

🔥 <i>Твой персональный музыкальный ассистент</i>

<b>✨ Возможности:</b>
🎯 Поиск с выбором из 5+ вариантов
🎭 Поиск по артисту
📜 Получение текстов песен
🎪 Умные рекомендации
📥 Скачивание в MP3

<b>⚠️ Примечание:</b>
Из-за ��егиональных ограничений некоторые видео могут быть недоступны.
Бот использует альтернативные методы поиска.

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
            "Напиши название песни, и я найду несколько вариантов для выбора 🎵\n\n"
            "<i>💡 Совет: Попробуй популярные песни для лучших результатов</i>",
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
            "Напиши название песни для получения текста 🎤\n\n"
            "<i>⚠️ Сервис текстов может быть временно недоступен</i>",
            parse_mode=ParseMode.HTML
        )
    
    elif query.data == "recommend":
        await show_recommendations(query.message, user_id)
    
    elif query.data.startswith("download_"):
        await handle_download(query, user_id)
    
    elif query.data.startswith("lyrics_"):
        await handle_lyrics_from_search(query, user_id)

async def show_recommendations(message, user_id):
    """Показ рекомендаций"""
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
        source_emoji = "🎵" if rec.get('source') == 'demo' else "🎶"
        text += f"{source_emoji} <b>{i+1}.</b> {rec['title']}\n"
        text += f"👤 {rec['uploader']}\n\n"
        
        keyboard.append([
            InlineKeyboardButton(f"📥 #{i+1}", callback_data=f"download_{i}"),
            InlineKeyboardButton(f"📜 #{i+1}", callback_data=f"lyrics_{i}")
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
    """Поиск песен"""
    loading_msg = await message.reply_text(
        "🔍 <b>Ищу песни...</b> ⚡\n\n"
        "<i>Пробую разные методы поиска...</i>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        results = get_cached_search(query, 6)
        await loading_msg.delete()
        
        if not results:
            await message.reply_text(
                f"❌ <b>Ничего не найдено:</b> <i>{query}</i>\n\n"
                "💡 Попробуйте:\n"
                "• Более популярные песни\n"
                "• Другое написание\n"
                "• Имя артиста + название",
                parse_mode=ParseMode.HTML
            )
            return
        
        user_search_results[user_id] = results
        
        text = f"🎵 <b>Найдено {len(results)} песен:</b> <i>{query}</i>\n\n"
        keyboard = []
        
        for i, result in enumerate(results):
            source_emoji = "🎵" if result.get('source') == 'demo' else "🎶"
            text += f"{source_emoji} <b>{i+1}.</b> {result['title']}\n"
            text += f"👤 {result['uploader']}\n"
            
            if result.get('source'):
                source_name = {
                    'youtube_direct': 'YouTube',
                    'youtube_proxy': 'YouTube (Proxy)',
                    'invidious': 'Invidious',
                    'demo': 'Demo'
                }.get(result['source'], result['source'])
                text += f"📡 {source_name}\n"
            
            text += "\n"
            
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
        await loading_msg.delete()
        await message.reply_text(f"❌ Ошибка поиска: {str(e)}")

async def handle_artist_search(message, artist_name, user_id):
    """Поиск по артисту"""
    loading_msg = await message.reply_text(
        f"🎭 <b>Ищу песни артиста...</b> ⚡\n\n"
        "<i>Использую все доступные методы...</i>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        store_artist(user_id, artist_name)
        results = get_cached_search(f"{artist_name} songs", 6)
        await loading_msg.delete()
        
        if not results:
            await message.reply_text(
                f"❌ <b>Артист не найден:</b> <i>{artist_name}</i>\n\n"
                "💡 Попробуйте более известных артистов",
                parse_mode=ParseMode.HTML
            )
            return
        
        user_search_results[user_id] = results
        
        text = f"🎭 <b>Песни артиста:</b> <i>{artist_name}</i>\n\n"
        keyboard = []
        
        for i, result in enumerate(results):
            source_emoji = "🎵" if result.get('source') == 'demo' else "🎶"
            text += f"{source_emoji} <b>{i+1}.</b> {result['title']}\n\n"
            
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
        await loading_msg.delete()
        await message.reply_text(f"❌ Ошибка поиска артиста: {str(e)}")

async def handle_lyrics_search(message, query):
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
                f"❌ <b>Не удалось найти текст для:</b> <i>{query}</i>\n\n"
                "⚠️ Сервис текстов временно недоступен из-за региональных ограничений",
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        await loading_msg.delete()
        await message.reply_text(f"❌ Ошибка получения текста: {str(e)}")

async def handle_download(query, user_id):
    try:
        index = int(query.data.split("_")[1])
        
        if user_id not in user_search_results or index >= len(user_search_results[user_id]):
            await query.message.reply_text("❌ Ошибка: песня не найдена")
            return
        
        selected_song = user_search_results[user_id][index]
        save_user_search(user_id, "download", selected_song)
        
        # Проверяем, это демо результат?
        if selected_song.get('source') == 'demo':
            await query.message.reply_text(
                f"⚠️ <b>Демо режим</b>\n\n"
                f"Это демонстрационный результат для: <i>{selected_song['title']}</i>\n\n"
                "Скачивание недоступно из-за региональных ограничений YouTube.\n\n"
                "💡 Попробуйте:\n"
                "• Использовать VPN\n"
                "• Другие музыкальные сервисы\n"
                "• Локальные источники музыки",
                parse_mode=ParseMode.HTML
            )
            return
        
        loading_msg = await query.message.reply_text(
            f"📥 <b>Скачиваю:</b> <i>{selected_song['title']}</i>\n⏳ Подождите...",
            parse_mode=ParseMode.HTML
        )
        
        try:
            # Очищаем старые файлы
            cleanup_old_files()
            
            # Скачиваем аудио
            audio_path = download_audio(selected_song['url'], selected_song['title'])
            
            if audio_path and os.path.exists(audio_path):
                try:
                    with open(audio_path, 'rb') as audio_file:
                        await query.message.reply_audio(
                            audio=audio_file,
                            title=selected_song['title'],
                            caption=f"🎵 <b>{selected_song['title']}</b>",
                            parse_mode=ParseMode.HTML
                        )
                    # Удаляем файл после отправки
                    os.remove(audio_path)
                    await loading_msg.delete()
                except Exception as e:
                    await loading_msg.edit_text(
                        f"❌ <b>Ошибка при отправке:</b> <i>{str(e)}</i>",
                        parse_mode=ParseMode.HTML
                    )
            else:
                await loading_msg.edit_text(
                    f"❌ <b>Не удалось скачать:</b> <i>{selected_song['title']}</i>\n\n"
                    f"Возможные причины:\n"
                    f"• Региональные ограничения\n"
                    f"• Видео недоступно\n"
                    f"• Проблемы с сетью\n\n"
                    f"Попробуйте другую песню из списка.",
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            await loading_msg.edit_text(
                f"❌ <b>Ошибка скачивания:</b> <i>{str(e)}</i>",
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
        
        # Проверяем, это демо результат?
        if selected_song.get('source') == 'demo':
            await query.message.reply_text(
                f"⚠️ <b>Демо режим</b>\n\n"
                f"Это демонстрационный результат для: <i>{selected_song['title']}</i>\n\n"
                "Получение текстов недоступно из-за ограничений API.",
                parse_mode=ParseMode.HTML
            )
            return
        
        loading_msg = await query.message.reply_text(
            f"📜 <b>Получаю текст:</b> <i>{selected_song['title']}</i>\n⏳ Подождите...",
            parse_mode=ParseMode.HTML
        )
        
        try:
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
                    f"❌ <b>Не удалось найти текст для:</b> <i>{selected_song['title']}</i>\n\n"
                    "⚠️ Сервис текстов временно недоступен",
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            await loading_msg.delete()
            await query.message.reply_text(f"❌ Ошибка получения текста: {str(e)}")
            
    except Exception as e:
        await query.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

# Webhook обработчики
async def webhook_handler(request):
    """Обработчик webhook от Telegram"""
    try:
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response(status=200)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return web.Response(status=500)

async def health_check(request):
    """Health check для Render"""
    return web.Response(text="🎵 Music Bot is running! ✅", status=200)

async def setup_webhook():
    """Настройка webhook"""
    webhook_url = f"https://supermusicbot.onrender.com/webhook"
    await app.bot.set_webhook(webhook_url)
    logger.info(f"Webhook установлен: {webhook_url}")

def create_app():
    """Создание веб-приложения"""
    web_app = web.Application()
    web_app.router.add_post('/webhook', webhook_handler)
    web_app.router.add_get('/', health_check)
    web_app.router.add_get('/health', health_check)
    return web_app

async def main():
    """Главная функция"""
    global app
    
    # Создаем папку для загрузок
    os.makedirs("downloads", exist_ok=True)
    
    # Создаем приложение бота
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Добавляем обработчик ошибок
    app.add_error_handler(error_handler)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # Инициализируем бота
    await app.initialize()
    await app.start()
    
    # Настраиваем webhook
    await setup_webhook()
    
    # Создаем веб-сервер
    web_app = create_app()
    
    port = int(os.environ.get('PORT', 10000))
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info("🎵 Music Bot запущен в WEBHOOK режиме!")
    logger.info("✨ Функции:")
    logger.info("   • Множественный выбор из 5+ песен")
    logger.info("   • Поиск по артисту")
    logger.info("   • Улучшенные рекомендации")
    logger.info("   • Альтернативные методы поиска")
    logger.info(f"   • Webhook сервер на порту {port}")
    
    # Держим сервер запущенным
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
