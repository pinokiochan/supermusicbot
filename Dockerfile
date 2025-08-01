FROM python:3.11-slim

# Устанавливаем системные зависимости включая ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем папку для загрузок с правильными правами
RUN mkdir -p downloads && chmod 777 downloads

# Запускаем бота
CMD ["python", "bot.py"]
