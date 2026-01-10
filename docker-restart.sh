#!/bin/bash

# Скрипт для полной пересборки и перезапуска Docker контейнера

echo "🔧 Остановка контейнера..."
docker-compose down

echo "🗑️  Удаление старого образа..."
docker rmi wd_block_notificator_app || true

echo "📦 Пересборка без кэша..."
docker-compose build --no-cache

echo "🚀 Запуск контейнера..."
docker-compose up -d

echo "📊 Логи:"
sleep 3
docker-compose logs -f
