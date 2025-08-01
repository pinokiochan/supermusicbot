import lyricsgenius
import re
from config import GENIUS_API_TOKEN

genius = lyricsgenius.Genius(GENIUS_API_TOKEN, timeout=15, skip_non_songs=True, verbose=False)

def clean_title(title):
    """Улучшенная очистка названия для поиска текста"""
    # Удаляем все в скобках
    title = re.sub(r"[$$\[].*?[$$\]]", "", title)
    # Удаляем ключевые слова
    title = re.sub(r"(official|video|hd|audio|lyrics|music|mv|feat|ft\.?)", "", title, flags=re.IGNORECASE)
    # Удаляем лишние пробелы и символы
    title = re.sub(r'\s+', ' ', title).strip()
    title = re.sub(r'[^\w\s-]', '', title)
    
    return title

def get_lyrics(title, artist=None):
    """Получение текста песни с улучшенным поиском"""
    try:
        cleaned_title = clean_title(title)
        
        # Пробуем разные варианты поиска
        search_variants = [
            cleaned_title,
            cleaned_title.split(' - ')[0] if ' - ' in cleaned_title else cleaned_title,
            ' '.join(cleaned_title.split()[:4])  # Первые 4 слова
        ]
        
        for variant in search_variants:
            try:
                if artist:
                    song = genius.search_song(variant, artist)
                else:
                    song = genius.search_song(variant)
                
                if song and song.lyrics:
                    # Очищаем текст
                    lyrics = song.lyrics
                    lyrics = re.sub(r'\d+Contributors.*$', '', lyrics, flags=re.DOTALL)
                    lyrics = re.sub(r'Embed$', '', lyrics)
                    lyrics = lyrics.strip()
                    
                    if len(lyrics) > 50:  # Проверяем, что текст не слишком короткий
                        return lyrics
            except:
                continue
        
        return None
    except Exception as e:
        print(f"Ошибка получения текста: {e}")
        return None

def search_artist_songs(artist_name, count=5):
    """Поиск песен конкретного артиста"""
    try:
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