from utils.ytsearch import search_youtube, search_youtube_multiple, user_search_history

user_last_artist = {}

def store_artist(user_id, artist):
    if artist:
        user_last_artist[user_id] = artist

def get_recommendations(user_id):
    """Улучшенные рекомендации - минимум 5 песен"""
    # Проверяем историю поиска
    if user_id in user_search_history and user_search_history[user_id]:
        return get_smart_recommendations_from_history(user_id)
    
    # Если нет истории, используем последнего артиста
    artist = user_last_artist.get(user_id)
    if not artist:
        return []
    
    return get_artist_recommendations(artist)

def get_smart_recommendations_from_history(user_id):
    """Быстрые умные рекомендации"""
    history = user_search_history[user_id]
    recommendations = []
    
    # Берем только последний поиск для скорости
    if history:
        last_search = history[-1]
        artist = last_search['artist']
        
        # Один быстрый поиск вместо нескольких
        quick_recs = search_youtube_multiple(f"{artist} top songs", 6)
        recommendations.extend(quick_recs)
    
    return recommendations[:6]

def get_artist_recommendations(artist):
    """Быстрые рекомендации по артисту"""
    # Один запрос вместо двух
    recs = search_youtube_multiple(f"{artist} popular hits", 6)
    return recs[:6]