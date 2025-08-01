import lyricsgenius
import re
from config import GENIUS_API_TOKEN
import requests
import time

# Инициализируем Genius API с улучшенными настройками
try:
    genius = lyricsgenius.Genius(
        GENIUS_API_TOKEN, 
        timeout=30, 
        skip_non_songs=True, 
        verbose=False,
        retries=3
    )
    genius.remove_section_headers = True
except Exception as e:
    print(f"Ошибка инициализации Genius API: {e}")
    genius = None

def clean_title_for_search(title):
    """Улучшенная очистка названия для поиска текста"""
    if not title:
        return "Unknown Title"
    
    # Удаляем все в скобках и кавычках
    title = re.sub(r'[$$\[].*?[$$\]]', '', title)
    title = re.sub(r'["""].*?["""]', '', title)
    
    # Удаляем ключевые слова
    keywords = [
        'official', 'video', 'hd', 'audio', 'lyrics', 'music', 'mv', 
        'feat', 'ft', 'featuring', 'remix', 'cover', 'live', 'acoustic',
        'version', 'remastered', 'extended', 'radio', 'edit'
    ]
    
    for keyword in keywords:
        title = re.sub(rf'\b{keyword}\b', '', title, flags=re.IGNORECASE)
    
    # Удаляем лишние символы и пробелы
    title = re.sub(r'[^\w\s-]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title if title else "Unknown Title"

def extract_artist_and_song(title):
    """Извлечение артиста и названия песни"""
    title = clean_title_for_search(title)
    
    # Пробуем разные разделители
    separators = [' - ', ' – ', ' — ', ' by ', ' | ']
    
    for sep in separators:
        if sep in title:
            parts = title.split(sep, 1)
            if len(parts) == 2:
                artist = parts[0].strip()
                song = parts[1].strip()
                return artist, song
    
    # Если разделитель не найден, берем первые слова как артиста
    words = title.split()
    if len(words) >= 3:
        artist = ' '.join(words[:2])
        song = ' '.join(words[2:])
        return artist, song
    
    return None, title

def get_lyrics(title, artist=None):
    """Получение текста песни с улучшенным поиском"""
    if not genius:
        return "❌ Genius API недоступен"
    
    try:
        # Извлекаем артиста и песню из названия
        if not artist:
            extracted_artist, song_title = extract_artist_and_song(title)
            artist = extracted_artist
            title = song_title
        
        print(f"Ищу текст: Артист='{artist}', Песня='{title}'")
        
        # Пробуем разные варианты поиска
        search_variants = []
        
        if artist:
            search_variants.extend([
                f"{artist} {title}",
                f"{title} {artist}",
                title
            ])
        else:
            search_variants.append(title)
        
        # Добавляем упрощенные варианты
        simple_title = ' '.join(title.split()[:4])  # Первые 4 слова
        if simple_title not in search_variants:
            search_variants.append(simple_title)
        
        for i, variant in enumerate(search_variants):
            try:
                print(f"Попытка {i+1}: '{variant}'")
                
                # Добавляем задержку между запросами
                if i > 0:
                    time.sleep(1)
                
                if artist and i == 0:
                    song = genius.search_song(title, artist)
                else:
                    song = genius.search_song(variant)
                
                if song and song.lyrics:
                    lyrics = song.lyrics
                    
                    # Очищаем текст
                    lyrics = re.sub(r'\d+Contributors.*$', '', lyrics, flags=re.DOTALL)
                    lyrics = re.sub(r'.*?Lyrics', '', lyrics, flags=re.DOTALL)
                    lyrics = re.sub(r'Embed$', '', lyrics)
                    lyrics = re.sub(r'You might also like.*$', '', lyrics, flags=re.DOTALL)
                    lyrics = lyrics.strip()
                    
                    if len(lyrics) > 50:  # Проверяем, что текст не слишком короткий
                        print(f"Найден текст длиной {len(lyrics)} символов")
                        return lyrics
                    
            except Exception as e:
                print(f"Ошибка в варианте {i+1}: {e}")
                continue
        
        return None
        
    except Exception as e:
        print(f"Общая ошибка получения текста: {e}")
        return None

def search_artist_songs(artist_name, count=5):
    """Поиск песен конкретного артиста"""
    if not genius:
        return []
    
    try:
        print(f"Ищу песни артиста: {artist_name}")
        artist_obj = genius.search_artist(artist_name, max_songs=count)
        
        if artist_obj and artist_obj.songs:
            songs_info = []
            for song in artist_obj.songs:
                songs_info.append({
                    'title': song.title,
                    'artist': song.artist,
                    'url': song.url
                })
            return songs_info
        return []
    except Exception as e:
        print(f"Ошибка поиска артиста: {e}")
        return []
