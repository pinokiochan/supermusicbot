from yt_dlp import YoutubeDL
import os

def download_audio(url, title="audio"):
    """Скачивание аудио с YouTube в mp3 (с fallback и логами ошибок)"""
    try:
        # Безопасное имя файла
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in (' ', '-', '_')).strip() or "audio"
        output_path = f"downloads/{safe_title}.%(ext)s"
        
        ydl_opts = {
            'format': 'bestaudio/best',  # больше не требуем m4a
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': True,
            'no_warnings': False,
            'socket_timeout': 15,
            'retries': 3,
            'user_agent': 'Mozilla/5.0'
        }
        
        os.makedirs("downloads", exist_ok=True)
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_file = f"downloads/{safe_title}.mp3"

            # Проверим итоговый mp3
            if os.path.exists(final_file):
                return final_file
            
            # Ищем файл по реальному названию
            real_title = info.get('title', safe_title)
            for file in os.listdir("downloads"):
                if real_title[:15] in file and file.endswith('.mp3'):
                    return f"downloads/{file}"
                    
        return None

    except Exception as e:
        print(f"[download_audio ERROR] {e}")
        return None
