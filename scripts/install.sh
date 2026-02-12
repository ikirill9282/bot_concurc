#!/bin/bash

# Скрипт автоматической установки бота без Docker
# Использование: bash scripts/install.sh

set -e

echo "🚀 Начинаем установку Colchuga Bot..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Пожалуйста, запустите скрипт от root${NC}"
    exit 1
fi

# Определение пути к проекту
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo -e "${GREEN}✓${NC} Директория проекта: $PROJECT_DIR"

# Шаг 1: Обновление системы
echo -e "\n${YELLOW}[1/8]${NC} Обновление системы..."
apt update && apt upgrade -y

# Шаг 2: Установка Python и PostgreSQL
echo -e "\n${YELLOW}[2/8]${NC} Установка Python и PostgreSQL..."
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git

# Проверка версии Python
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓${NC} Python версия: $PYTHON_VERSION"

# Шаг 3: Настройка PostgreSQL
echo -e "\n${YELLOW}[3/8]${NC} Настройка PostgreSQL..."

# Запрос пароля для базы данных
read -sp "Введите пароль для пользователя базы данных: " DB_PASSWORD
echo ""
read -sp "Подтвердите пароль: " DB_PASSWORD_CONFIRM
echo ""

if [ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]; then
    echo -e "${RED}❌ Пароли не совпадают!${NC}"
    exit 1
fi

# Создание базы данных и пользователя
sudo -u postgres psql <<EOF
CREATE DATABASE giveaway_bot;
CREATE USER bot_user WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE giveaway_bot TO bot_user;
\q
EOF

echo -e "${GREEN}✓${NC} База данных создана"

# Шаг 4: Создание виртуального окружения
echo -e "\n${YELLOW}[4/8]${NC} Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Шаг 5: Установка зависимостей
echo -e "\n${YELLOW}[5/8]${NC} Установка зависимостей Python..."
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✓${NC} Зависимости установлены"

# Шаг 6: Настройка .env
echo -e "\n${YELLOW}[6/8]${NC} Настройка переменных окружения..."

if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓${NC} Файл .env создан из примера"
else
    echo -e "${YELLOW}⚠${NC} Файл .env уже существует, пропускаем"
fi

# Обновление DATABASE_URL в .env
sed -i "s|postgresql+asyncpg://postgres:postgres@db:5432/giveaway_bot|postgresql+asyncpg://bot_user:$DB_PASSWORD@localhost:5432/giveaway_bot|g" .env

# Запрос остальных параметров
read -p "Введите BOT_TOKEN от @BotFather: " BOT_TOKEN
read -p "Введите CHANNEL_ID (формат: -1001234567890): " CHANNEL_ID
read -p "Введите ADMIN_IDS (через запятую): " ADMIN_IDS
read -p "Введите BOT_USERNAME (без @): " BOT_USERNAME

# Обновление .env
sed -i "s|BOT_TOKEN=.*|BOT_TOKEN=$BOT_TOKEN|g" .env
sed -i "s|CHANNEL_ID=.*|CHANNEL_ID=$CHANNEL_ID|g" .env
sed -i "s|ADMIN_IDS=.*|ADMIN_IDS=$ADMIN_IDS|g" .env
sed -i "s|BOT_USERNAME=.*|BOT_USERNAME=$BOT_USERNAME|g" .env
sed -i "s|SKIP_WEBHOOK_SETUP=.*|SKIP_WEBHOOK_SETUP=true|g" .env
sed -i "s|APP_HOST=.*|APP_HOST=127.0.0.1|g" .env

echo -e "${GREEN}✓${NC} Переменные окружения настроены"

# Шаг 7: Применение миграций
echo -e "\n${YELLOW}[7/8]${NC} Применение миграций базы данных..."
export DATABASE_URL="postgresql+asyncpg://bot_user:$DB_PASSWORD@localhost:5432/giveaway_bot"
alembic upgrade head

echo -e "${GREEN}✓${NC} Миграции применены"

# Шаг 8: Создание systemd сервиса
echo -e "\n${YELLOW}[8/8]${NC} Создание systemd сервиса..."

cat > /etc/systemd/system/colchuga-bot.service <<EOF
[Unit]
Description=Colchuga Telegram Bot
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python -m app.main
Restart=always
RestartSec=10

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=colchuga-bot

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable colchuga-bot

echo -e "${GREEN}✓${NC} Systemd сервис создан"

# Итог
echo -e "\n${GREEN}✅ Установка завершена!${NC}"
echo -e "\nДля запуска бота выполните:"
echo -e "  ${YELLOW}sudo systemctl start colchuga-bot${NC}"
echo -e "\nДля просмотра логов:"
echo -e "  ${YELLOW}sudo journalctl -u colchuga-bot -f${NC}"
echo -e "\nДля проверки статуса:"
echo -e "  ${YELLOW}sudo systemctl status colchuga-bot${NC}"
