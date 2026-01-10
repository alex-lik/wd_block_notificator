# Используем базовый образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt первым (для кэширования)
COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV TZ=Europe/Kiev

# Определяем команду для запуска приложения
CMD ["python", "main.py"]
