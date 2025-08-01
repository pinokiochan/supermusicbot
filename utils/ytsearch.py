from yt_dlp import YoutubeDL
import re

history = {}
user_search_history = {}

def search_youtube_multiple(query, count=6):
    """Быстрый поиск нескольких песен по запросу"""
    try:
        # Оптимизированные настройки для скорости
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Не извлекаем полную информацию
            'skip_download': True,
            'ignoreerrors': True,
            'socket_timeout': 10,  # Таймаут 10 секунд
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            # Ищем больше результатов за один запрос
            search_results = ydl.extract_info(f"ytsearch{count + 2}:{query}", download=False)
            
            results = []
            if 'entries' in search_results:
                for i, entry in enumerate(search_results['entries'][:count]):
                    if entry and entry.get('id'):
                        # Минимальная обработка для скорости
                        title = entry.get('title', 'Unknown Title')
                        # Быстрая очистка без regex
                        title = title.replace('[Official Video]', '').replace('(Official Video)', '')
                        title = title.replace('[Official Audio]', '').replace('(Official Audio)', '')
                        title = title.strip()
                        
                        results.append({
                            'index': i,
                            'title': title,
                            'url': f"https://www.youtube.com/watch?v={entry['id']}",
                            'duration': "N/A",  # Не получаем длительность для скорости
                            'uploader': entry.get('uploader', 'YouTube'),
                            'id': entry['id']
                        })
            
            return results
    except Exception as e:
        print(f"Ошибка поиска: {e}")
        return []

def search_youtube(query):
    """Оригинальная функция - оставляем для совместимости"""
    try:
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
            title = info['title']
            url = info['webpage_url']

            # сохраняем в историю для рекомендаций
            if query not in history:
                history[query] = []
            history[query].append(title)

            return {'title': title, 'url': url}
    except:
        return None

def clean_title(title):
    """Быстрая очистка названия"""
    if not title:
        return "Unknown Title"
    
    # Простая замена без regex для скорости
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
    
    # Сохраняем последние 10 поисков
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
        return []
    
    user_history = user_search_history[user_id]
    recommendations = []
    
    # Берем последние 3 поиска
    recent_searches = user_history[-3:]
    
    for search_data in recent_searches:
        artist = search_data['artist']
        
        # Ищем похожие песни по артисту
        similar_songs = search_youtube_multiple(f"{artist} popular songs", 3)
        for song in similar_songs:
            if song not in recommendations:
                recommendations.append(song)
        
        # Ищем по жанру/стилю
        genre_songs = search_youtube_multiple(f"similar to {search_data['song']['title']}", 2)
        for song in genre_songs:
            if song not in recommendations:
                recommendations.append(song)
    
    return recommendations[:count] if recommendations else []