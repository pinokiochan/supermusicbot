from yt_dlp import YoutubeDL
import re
from utils.proxy_youtube import search_youtube_via_proxy, search_invidious
from utils.alternative_sources import get_alternative_sources
import logging

logger = logging.getLogger(__name__)

history = {}
user_search_history = {}

def search_youtube_multiple(query, count=6):
    """Поиск с использованием всех доступных методов"""
    try:
        logger.info(f"Начинаю поиск: {query}")
        
        # Метод 1: Прямой поиск YouTube (может не работать)
        results = search_youtube_direct(query, count)
        if len(results) >= 3:
            logger.info(f"Прямой поиск успешен: {len(results)} результатов")
            return results
        
        # Метод 2: Поиск через прокси API
        logger.info("Пробую поиск через прокси...")
        proxy_results = search_youtube_via_proxy(query, count)
        if len(proxy_results) >= 3:
            logger.info(f"Прокси поиск успешен: {len(proxy_results)} результатов")
            return proxy_results
        
        # Метод 3: Поиск через Invidious
        logger.info("Пробую поиск через Invidious...")
        invidious_results = search_invidious(query, count)
        if len(invidious_results) >= 3:
            logger.info(f"Invidious поиск успешен: {len(invidious_results)} результатов")
            return invidious_results
        
        # Метод 4: Альтернативные источники
        logger.info("Пробую альтернативные источники...")
        alt_results = get_alternative_sources(query, count)
        if alt_results:
            logger.info(f"Альтернативные источники: {len(alt_results)} результатов")
            return alt_results
        
        # Если ничего не найдено, возвращаем демо-результаты
        logger.warning("Все методы поиска не дали результатов, возвращаю демо")
        return get_demo_results(query, count)
        
    except Exception as e:
        logger.error(f"Общая ошибка поиска: {e}")
        return get_demo_results(query, count)

def search_youtube_direct(query, count=6):
    """Прямой поиск YouTube (оригинальный метод)"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
            'ignoreerrors': True,
            'socket_timeout': 10,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch{count + 2}:{query}", download=False)
            
            results = []
            if 'entries' in search_results:
                for i, entry in enumerate(search_results['entries'][:count]):
                    if entry and entry.get('id'):
                        title = entry.get('title', 'Unknown Title')
                        title = clean_title(title)
                        
                        results.append({
                            'index': i,
                            'title': title,
                            'url': f"https://www.youtube.com/watch?v={entry['id']}",
                            'duration': "N/A",
                            'uploader': entry.get('uploader', 'YouTube'),
                            'id': entry['id'],
                            'source': 'youtube_direct'
                        })
            
            return results
            
    except Exception as e:
        logger.error(f"Ошибка прямого поиска: {e}")
        return []

def get_demo_results(query, count=6):
    """Демо результаты когда ничего не работает"""
    demo_songs = [
        {
            'index': 0,
            'title': f'🎵 Поиск: {query} - Результат 1',
            'url': 'https://www.youtube.com/watch?v=demo1',
            'duration': '3:45',
            'uploader': 'Demo Channel',
            'id': 'demo1',
            'source': 'demo'
        },
        {
            'index': 1,
            'title': f'🎵 Поиск: {query} - Результат 2',
            'url': 'https://www.youtube.com/watch?v=demo2',
            'duration': '4:12',
            'uploader': 'Demo Music',
            'id': 'demo2',
            'source': 'demo'
        },
        {
            'index': 2,
            'title': f'🎵 Поиск: {query} - Результат 3',
            'url': 'https://www.youtube.com/watch?v=demo3',
            'duration': '3:28',
            'uploader': 'Demo Artist',
            'id': 'demo3',
            'source': 'demo'
        }
    ]
    
    return demo_songs[:count]

def search_youtube(query):
    """Оригинальная функция - оставляем для совместимости"""
    results = search_youtube_multiple(query, 1)
    if results:
        return {'title': results[0]['title'], 'url': results[0]['url']}
    return None

def clean_title(title):
    """Быстрая очистка названия"""
    if not title:
        return "Unknown Title"
    
    replacements = ['[Official Video]', '(Official Video)', '[Official Audio]', '(Official Audio)', 
                   '[HD]', '(HD)', '[4K]', '(4K)', 'Official', 'Video', 'Audio']
    
    for replacement in replacements:
        title = title.replace(replacement, '')
    
    return title.strip() or "Unknown Title"

def format_duration(seconds):
    """Форматирование длительности"""
    if not seconds:
        return "N/A"
    
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def save_user_search(user_id, query, selected_song):
    """Сохранение поиска пользователя для рекомендаций"""
    if user_id not in user_search_history:
        user_search_history[user_id] = []
    
    search_data = {
        'query': query,
        'song': selected_song,
        'artist': extract_artist_from_title(selected_song['title'])
    }
    
    user_search_history[user_id].append(search_data)
    
    if len(user_search_history[user_id]) > 10:
        user_search_history[user_id].pop(0)

def extract_artist_from_title(title):
    """Извлечение артиста из названия"""
    if ' - ' in title:
        return title.split(' - ')[0].strip()
    elif ' by ' in title.lower():
        return title.lower().split(' by ')[1].strip()
    else:
        words = title.split()
        return ' '.join(words[:2]) if len(words) >= 2 else title

def get_recommendations():
    """Оригинальная функция рекомендаций"""
    if not history:
        return ["Нет истории для рекомендаций."]
    
    last_query = list(history.keys())[-1]
    return [f"Похожее на: {last_query}"]

def get_smart_recommendations(user_id, count=6):
    """Умные рекомендации на основе истории пользователя"""
    if user_id not in user_search_history or not user_search_history[user_id]:
        return get_demo_results("популярная музыка", count)
    
    user_history = user_search_history[user_id]
    recommendations = []
    
    recent_searches = user_history[-3:]
    
    for search_data in recent_searches:
        artist = search_data['artist']
        
        similar_songs = search_youtube_multiple(f"{artist} popular songs", 3)
        for song in similar_songs:
            if song not in recommendations:
                recommendations.append(song)
        
        if len(recommendations) >= count:
            break
    
    return recommendations[:count] if recommendations else get_demo_results("рекомендации", count)
