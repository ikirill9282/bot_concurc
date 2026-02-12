#!/bin/bash
# Скрипт автоматического развертывания на сервере
# Использование: ./scripts/deploy.sh

set -e

echo "🚀 Начало развертывания Colchuga Bot..."

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker сначала."
    exit 1
fi

# Проверка наличия docker compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose сначала."
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Создаю из .env.example..."
    cp .env.example .env
    echo "📝 Пожалуйста, заполните файл .env перед продолжением!"
    echo "   Откройте .env и заполните все необходимые переменные."
    exit 1
fi

# Проверка наличия SSL сертификатов
if [ ! -f nginx/certs/fullchain.pem ] || [ ! -f nginx/certs/privkey.pem ]; then
    echo "⚠️  SSL сертификаты не найдены в nginx/certs/"
    echo "📝 Для получения сертификатов выполните:"
    echo "   sudo certbot certonly --standalone -d your-domain.com"
    echo "   sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/certs/"
    echo "   sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/certs/"
    echo "   sudo chown \$USER:\$USER nginx/certs/*.pem"
    read -p "Продолжить без SSL? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Остановка существующих контейнеров
echo "🛑 Остановка существующих контейнеров..."
docker compose down 2>/dev/null || true

# Сборка и запуск
echo "🔨 Сборка образов..."
docker compose build

echo "🚀 Запуск контейнеров..."
docker compose up -d

# Ожидание готовности сервисов
echo "⏳ Ожидание готовности сервисов..."
sleep 10

# Проверка статуса
echo "📊 Проверка статуса контейнеров..."
docker compose ps

# Проверка health endpoints
echo "🏥 Проверка health endpoints..."
if command -v curl &> /dev/null; then
    # Попытка получить домен из .env
    WEBHOOK_URL=$(grep WEBHOOK_URL .env | cut -d '=' -f2 | tr -d '"' | tr -d "'" | sed 's|/webhook||')
    if [ ! -z "$WEBHOOK_URL" ]; then
        echo "Проверка $WEBHOOK_URL/healthz..."
        curl -f -s "$WEBHOOK_URL/healthz" && echo "✅ Health check passed" || echo "⚠️  Health check failed"
    fi
fi

echo ""
echo "✅ Развертывание завершено!"
echo ""
echo "📋 Полезные команды:"
echo "   Просмотр логов:    docker compose logs -f"
echo "   Перезапуск:        docker compose restart"
echo "   Остановка:         docker compose down"
echo "   Статус:            docker compose ps"
echo ""
