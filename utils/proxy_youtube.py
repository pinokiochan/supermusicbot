import requests
import json
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

def search_youtube_via_proxy(query, count=6):
    """Поиск YouTube через прокси API"""
    try:
        # Используем публичные YouTube API прокси
        proxy_apis = [
            "https://youtube-search-api.vercel.app/api/search",
            "https://yt-search-api.herokuapp.com/search",
            "https://youtube-api-proxy.herokuapp.com/search"
        ]
        
        for api_url in proxy_apis:
            try:
                params = {
                    'q': query,
                    'maxResults': count + 3
                }
                
                response = requests.get(api_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    results = []
                    items = data.get('items', []) or data.get('results', [])
                    
                    for i, item in enumerate(items[:count]):
                        if item.get('id'):
                            video_id = item['id'].get('videoId') if isinstance(item['id'], dict) else item['id']
                            
                            results.append({
                                'index': i,
                                'title': item.get('title', 'Unknown Title'),
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'duration': item.get('duration', 'N/A'),
                                'uploader': item.get('channelTitle', 'YouTube'),
                                'id': video_id,
                                'source': 'youtube_proxy'
                            })
                    
                    if results:
                        logger.info(f"Найдено {len(results)} результатов через прокси")
                        return results
                        
            except Exception as e:
                logger.error(f"Ошибка прокси API {api_url}: {e}")
                continue
        
        return []
        
    except Exception as e:
        logger.error(f"Общая ошибка прокси поиска: {e}")
        return []

def search_invidious(query, count=6):
    """Поиск через Invidious (альтернативный YouTube фронтенд)"""
    try:
        # Публичные Invidious инстансы
        invidious_instances = [
            "https://invidious.io",
            "https://yewtu.be",
            "https://invidious.snopyta.org"
        ]
        
        for instance in invidious_instances:
            try:
                search_url = f"{instance}/api/v1/search"
                params = {
                    'q': query,
                    'type': 'video',
                    'sort_by': 'relevance'
                }
                
                response = requests.get(search_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    results = []
                    for i, item in enumerate(data[:count]):
                        if item.get('videoId'):
                            results.append({
                                'index': i,
                                'title': item.get('title', 'Unknown Title'),
                                'url': f"https://www.youtube.com/watch?v={item['videoId']}",
                                'duration': item.get('lengthSeconds', 'N/A'),
                                'uploader': item.get('author', 'YouTube'),
                                'id': item['videoId'],
                                'source': 'invidious'
                            })
                    
                    if results:
                        logger.info(f"Найдено {len(results)} результатов через Invidious")
                        return results
                        
            except Exception as e:
                logger.error(f"Ошибка Invidious {instance}: {e}")
                continue
        
        return []
        
    except Exception as e:
        logger.error(f"Общая ошибка Invidious: {e}")
        return []
