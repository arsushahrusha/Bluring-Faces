FROM python:3.9-slim

# Устанавливаем системные зависимости для OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements первыми для кэширования
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем ВСЮ структуру проекта
COPY . .

# Создаем директорию для статических файлов
RUN mkdir -p static

# Добавляем папку backend в PYTHONPATH
ENV PYTHONPATH="/app/backend:${PYTHONPATH}"

# Открываем порт
EXPOSE 8000

# Запускаем приложение из папки backend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
