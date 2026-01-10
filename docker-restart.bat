@echo off
REM Скрипт для полной пересборки и перезапуска Docker контейнера на Windows

echo 🔧 Остановка контейнера...
docker-compose down

echo 🗑️  Удаление старого образа...
docker rmi wd_block_notificator_app 2>nul

echo 📦 Пересборка без кэша...
docker-compose build --no-cache

echo 🚀 Запуск контейнера...
docker-compose up -d

echo 📊 Ожидание запуска (3 сек)...
timeout /t 3 /nobreak

echo 📊 Логи:
docker-compose logs -f
