# Быстрая установка - Шпаргалка

## Автоматическая установка (рекомендуется)

```bash
# Загрузите проект на сервер, затем:
cd ~/projects/colchuga_bot
bash scripts/install.sh
```

Скрипт автоматически:
- Установит все зависимости
- Настроит PostgreSQL
- Создаст виртуальное окружение
- Настроит .env
- Применит миграции
- Создаст systemd сервис

---

## Ручная установка (5 минут)

### 1. Установка зависимостей

```bash
apt update && apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git
```

### 2. Настройка PostgreSQL

```bash
sudo -u postgres psql
```

В psql:
```sql
CREATE DATABASE giveaway_bot;
CREATE USER bot_user WITH PASSWORD 'ваш_пароль';
GRANT ALL PRIVILEGES ON DATABASE giveaway_bot TO bot_user;
\q
```

### 3. Настройка проекта

```bash
cd ~/projects/colchuga_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env  # Заполните все переменные!
```

**Минимальный .env для работы БЕЗ домена:**

```env
BOT_TOKEN=ваш_токен
DATABASE_URL=postgresql+asyncpg://bot_user:пароль@localhost:5432/giveaway_bot
CHANNEL_ID=-1001234567890
ADMIN_IDS=123456789
SKIP_WEBHOOK_SETUP=true
BOT_USERNAME=your_bot_username
```

### 4. Миграции и запуск

```bash
source venv/bin/activate
alembic upgrade head
python -m app.main  # Тестовый запуск
```

### 5. Systemd сервис

```bash
sudo nano /etc/systemd/system/colchuga-bot.service
```

Вставьте (замените пути!):
```ini
[Unit]
Description=Colchuga Telegram Bot
After=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/projects/colchuga_bot
Environment="PATH=/root/projects/colchuga_bot/venv/bin"
ExecStart=/root/projects/colchuga_bot/venv/bin/python -m app.main
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable colchuga-bot
sudo systemctl start colchuga-bot
```

---

## Команды управления

```bash
# Статус
sudo systemctl status colchuga-bot

# Запуск/Остановка/Перезапуск
sudo systemctl start colchuga-bot
sudo systemctl stop colchuga-bot
sudo systemctl restart colchuga-bot

# Логи
sudo journalctl -u colchuga-bot -f
```

---

## Обновление

```bash
cd ~/projects/colchuga_bot
sudo systemctl stop colchuga-bot
git pull  # или обновите файлы вручную
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl start colchuga-bot
```

---

## Размер установки

- Python + зависимости: ~150 MB
- PostgreSQL: ~150 MB
- **Итого: ~300 MB** (вместо 2-3 GB с Docker)

---

## Преимущества

✅ Нет Docker - экономия места  
✅ Простые команды systemctl  
✅ Быстрый запуск  
✅ Легкая отладка  
