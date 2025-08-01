from yt_dlp import YoutubeDL
import os
import re
import tempfile
import logging
import time
import shutil
import subprocess

logger = logging.getLogger(__name__)

def check_ffmpeg():
    """Проверка наличия ffmpeg"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("✅ FFmpeg найден и работает")
            return True
        else:
            logger.error("❌ FFmpeg не работает")
            return False
    except Exception as e:
        logger.error(f"❌ FFmpeg не найден: {e}")
        return False

def download_audio(url, title="audio"):
    """Улучшенное скачивание аудио с проверкой ffmpeg"""
    try:
        # Проверяем ffmpeg
        if not check_ffmpeg():
            logger.error("FFmpeg недоступен - скачивание невозможно")
            return None
        
        # Создаем безопасное имя файла
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in (' ', '-', '_'))
        safe_title = safe_title.strip() or "audio"
        safe_title = re.sub(r'\s+', '_', safe_title)
        
        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, f"{safe_title}.%(ext)s")
        
        # Улучшенные настройки для Render
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
            'outtmpl': output_template,
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
            'ignoreerrors': False,  # Не игнорируем ошибки для лучшей диагностики
        }
        
        logger.info(f"Скачиваю: {url}")
        
        with YoutubeDL(ydl_opts) as ydl:
            # Сначала получаем информацию о видео
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    logger.error("Не удалось получить информацию о видео")
                    return None
                
                # Проверяем доступность
                if info.get('availability') == 'private':
                    logger.error("Видео приватное")
                    return None
                    
                if info.get('live_status') == 'is_live':
                    logger.error("Это прямая трансляция - скачивание невозможно")
                    return None
                    
            except Exception as e:
                logger.error(f"Ошибка получения информации о видео: {e}")
                return None
            
            # Теперь скачиваем
            try:
                ydl.download([url])
            except Exception as e:
                logger.error(f"Ошибка скачивания: {e}")
                return None
        
        # Ищем скачанный файл
        mp3_file = os.path.join(temp_dir, f"{safe_title}.mp3")
        
        if os.path.exists(mp3_file):
            # Перемещаем в downloads
            final_path = f"downloads/{safe_title}_{int(time.time())}.mp3"
            os.makedirs("downloads", exist_ok=True)
            
            shutil.move(mp3_file, final_path)
            
            # Удаляем временную директорию
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            logger.info(f"✅ Файл сохранен: {final_path}")
            return final_path
        else:
            # Ищем любой mp3 файл в temp_dir
            for file in os.listdir(temp_dir):
                if file.endswith('.mp3'):
                    temp_file = os.path.join(temp_dir, file)
                    final_path = f"downloads/{safe_title}_{int(time.time())}.mp3"
                    os.makedirs("downloads", exist_ok=True)
                    
                    shutil.move(temp_file, final_path)
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
                    logger.info(f"✅ Файл сохранен: {final_path}")
                    return final_path
            
            # Удаляем временную директорию
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.error("MP3 файл не найден после конвертации")
            return None
                        
    except Exception as e:
        logger.error(f"❌ Общая ошибка при скачивании: {e}")
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
                        logger.info(f"Удален старый файл: {file}")
                    except Exception as e:
                        logger.error(f"Ошибка удаления файла {file}: {e}")
    except Exception as e:
        logger.error(f"Ошибка при очистке: {e}")
