from yt_dlp import YoutubeDL
import os
import re
import tempfile
import logging

logger = logging.getLogger(__name__)

def download_audio(url, title="audio"):
    """Простое и надежное скачивание аудио"""
    try:
        # Создаем безопасное имя файла
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in (' ', '-', '_'))
        safe_title = safe_title.strip() or "audio"
        safe_title = re.sub(r'\s+', '_', safe_title)
        
        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, f"{safe_title}.%(ext)s")
        
        # Простые настройки для надежности
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 1,
        }
        
        logger.info(f"Скачиваю: {url}")
        
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Ищем скачанный файл
        mp3_file = os.path.join(temp_dir, f"{safe_title}.mp3")
        
        if os.path.exists(mp3_file):
            # Перемещаем в downloads
            final_path = f"downloads/{safe_title}_{int(time.time())}.mp3"
            os.makedirs("downloads", exist_ok=True)
            
            import shutil
            shutil.move(mp3_file, final_path)
            
            # Удаляем временную директорию
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            logger.info(f"Файл сохранен: {final_path}")
            return final_path
        else:
            # Ищем любой mp3 файл в temp_dir
            for file in os.listdir(temp_dir):
                if file.endswith('.mp3'):
                    temp_file = os.path.join(temp_dir, file)
                    final_path = f"downloads/{safe_title}_{int(time.time())}.mp3"
                    os.makedirs("downloads", exist_ok=True)
                    
                    import shutil
                    shutil.move(temp_file, final_path)
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
                    return final_path
            
            # Удаляем временную директорию
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
                        
    except Exception as e:
        logger.error(f"Ошибка при скачивании: {e}")
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
        logger.error(f"Ошибка при очистке: {e}")
