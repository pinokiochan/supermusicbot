from yt_dlp import YoutubeDL
import os
import re

def download_audio(url, title="audio"):
    """Быстрое скачивание аудио с YouTube"""
    try:
        # Создаем безопасное имя файла быстро
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in (' ', '-', '_'))
        safe_title = safe_title.strip() or "audio"
        
        output_path = f"downloads/{safe_title}.%(ext)s"
        
        # Оптимизированные настройки для скорости
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',  # Предпочитаем m4a для скорости
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',  # Уменьшаем качество для скорости
            }],
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 15,
            'retries': 1,  # Меньше попыток
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            filename = f"downloads/{safe_title}.mp3"
            
            # Быстрая проверка файла
            if os.path.exists(filename):
                return filename
            else:
                # Быстрый поиск файла
                for file in os.listdir("downloads"):
                    if safe_title[:15] in file and file.endswith('.mp3'):
                        return f"downloads/{file}"
                        
        return None
    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
        return None

def cleanup_old_files():
    """Очистка старых файлов"""
    try:
        downloads_dir = "downloads"
        if os.path.exists(downloads_dir):
            files = os.listdir(downloads_dir)
            if len(files) > 10:  # Если больше 10 файлов, удаляем старые
                files.sort(key=lambda x: os.path.getctime(os.path.join(downloads_dir, x)))
                for file in files[:-5]:  # Оставляем только 5 новых
                    os.remove(os.path.join(downloads_dir, file))
    except Exception as e:
        print(f"Ошибка при очистке: {e}")