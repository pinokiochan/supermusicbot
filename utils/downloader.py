from yt_dlp import YoutubeDL
import os
import re
import tempfile

def download_audio(url, title="audio"):
    """Улучшенное скачивание аудио с YouTube для Render"""
    try:
        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        
        # Создаем безопасное имя файла
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in (' ', '-', '_'))
        safe_title = safe_title.strip() or "audio"
        safe_title = re.sub(r'\s+', '_', safe_title)
        
        output_path = os.path.join(temp_dir, f"{safe_title}.%(ext)s")
        
        # Оптимизированные настройки для Render
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 2,
            'fragment_retries': 2,
            'extractaudio': True,
            'audioformat': 'mp3',
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            print(f"Скачиваю: {url}")
            ydl.download([url])
            
            # Ищем скачанный файл
            mp3_file = os.path.join(temp_dir, f"{safe_title}.mp3")
            
            if os.path.exists(mp3_file):
                # Перемещаем в downloads
                final_path = f"downloads/{safe_title}.mp3"
                os.makedirs("downloads", exist_ok=True)
                
                # Копируем файл
                with open(mp3_file, 'rb') as src, open(final_path, 'wb') as dst:
                    dst.write(src.read())
                
                # Удаляем временный файл
                os.remove(mp3_file)
                os.rmdir(temp_dir)
                
                print(f"Файл сохранен: {final_path}")
                return final_path
            else:
                # Ищем любой mp3 файл в temp_dir
                for file in os.listdir(temp_dir):
                    if file.endswith('.mp3'):
                        temp_file = os.path.join(temp_dir, file)
                        final_path = f"downloads/{safe_title}.mp3"
                        os.makedirs("downloads", exist_ok=True)
                        
                        with open(temp_file, 'rb') as src, open(final_path, 'wb') as dst:
                            dst.write(src.read())
                        
                        os.remove(temp_file)
                        os.rmdir(temp_dir)
                        return final_path
                
                print("MP3 файл не найден после конвертации")
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
            if len(files) > 10:
                files.sort(key=lambda x: os.path.getctime(os.path.join(downloads_dir, x)))
                for file in files[:-5]:
                    try:
                        os.remove(os.path.join(downloads_dir, file))
                    except:
                        pass
    except Exception as e:
        print(f"Ошибка при очистке: {e}")
