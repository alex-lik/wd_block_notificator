# Используем базовый образ Python
FROM python:3.12-slim

# Устанавливаем зависимости
# RUN apt-get update && apt-get install -y \
#     build-essential \
#     libssl-dev \
#     libffi-dev \
#     libxml2-dev \
#     libxslt1-dev \
#     zlib1g-dev \
#     libjpeg-dev \
#     python3-dev \
#     default-libmysqlclient-dev

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . .

# Устанавливаем необходимые пакеты Python
RUN pip install --no-cache-dir -r requirements.txt

# Определяем команду для запуска приложения
CMD ["python", "main.py"]
