# Простое развертывание без Docker

## Быстрый старт (5 минут)

### 1. Подключение к серверу

```bash
ssh root@your-server-ip
```

### 2. Установка Python и PostgreSQL

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Python 3.11+ и необходимых пакетов
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git

# Проверка версии Python (должна быть 3.11+)
python3 --version
```

### 3. Настройка PostgreSQL

```bash
# Переключение на пользователя postgres
sudo -u postgres psql

# В psql выполните:
CREATE DATABASE giveaway_bot;
CREATE USER bot_user WITH PASSWORD 'ваш_надежный_пароль';
GRANT ALL PRIVILEGES ON DATABASE giveaway_bot TO bot_user;
\q
```

### 4. Загрузка проекта

```bash
# Создание директории
mkdir -p ~/projects
cd ~/projects

# Загрузка проекта (выберите один вариант)

# Вариант A: Через Git
git clone <your-repo-url> colchuga_bot
cd colchuga_bot

# Вариант B: Через SCP (с вашего компьютера)
# На вашем компьютере:
# scp -r /path/to/colchuga_bot user@server:~/projects/
# Затем на сервере:
# cd ~/projects/colchuga_bot
```

### 5. Настройка виртуального окружения

```bash
cd ~/projects/colchuga_bot

# Создание виртуального окружения
python3 -m venv venv

# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Настройка переменных окружения

```bash
# Копирование примера
cp .env.example .env

# Редактирование .env
nano .env
```

**Минимальная конфигурация для работы БЕЗ домена:**

```env
BOT_TOKEN=ваш_токен_от_botfather
DATABASE_URL=postgresql+asyncpg://bot_user:ваш_надежный_пароль@localhost:5432/giveaway_bot
CHANNEL_ID=-1001234567890
ADMIN_IDS=123456789

# Важно! Для работы без домена:
SKIP_WEBHOOK_SETUP=true
BOT_USERNAME=your_bot_username_without_at

LOG_LEVEL=INFO
APP_HOST=127.0.0.1
APP_PORT=8080
```

**Важно:**
- Замените `ваш_токен_от_botfather` на токен от @BotFather
- Замените `ваш_надежный_пароль` на пароль, который вы указали при создании пользователя PostgreSQL
- Замените `CHANNEL_ID` на ID вашего канала (формат: -100xxxxxxxxxx)
- Замените `ADMIN_IDS` на ваш Telegram ID (можно узнать у @userinfobot)
- Замените `your_bot_username_without_at` на имя вашего бота без @

### 7. Применение миграций базы данных

```bash
# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate

# Обновление DATABASE_URL в alembic.ini (если нужно)
# Или используйте переменную окружения
export DATABASE_URL="postgresql+asyncpg://bot_user:пароль@localhost:5432/giveaway_bot"

# Применение миграций
alembic upgrade head
```

### 8. Тестовый запуск

```bash
# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate

# Запуск бота
python -m app.main
```

Если всё работает, остановите бота (Ctrl+C) и переходите к следующему шагу.

### 9. Настройка автозапуска через systemd

```bash
# Создание файла сервиса
sudo nano /etc/systemd/system/colchuga-bot.service
```

Добавьте следующее содержимое (замените пути на ваши):

```ini
[Unit]
Description=Colchuga Telegram Bot
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/projects/colchuga_bot
Environment="PATH=/root/projects/colchuga_bot/venv/bin"
ExecStart=/root/projects/colchuga_bot/venv/bin/python -m app.main
Restart=always
RestartSec=10

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=colchuga-bot

[Install]
WantedBy=multi-user.target
```

**Важно:** Замените `/root/projects/colchuga_bot` на ваш реальный путь к проекту.

### 10. Запуск сервиса

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable colchuga-bot

# Запуск бота
sudo systemctl start colchuga-bot

# Проверка статуса
sudo systemctl status colchuga-bot

# Просмотр логов
sudo journalctl -u colchuga-bot -f
```

---

## Полезные команды

### Управление ботом

```bash
# Статус
sudo systemctl status colchuga-bot

# Запуск
sudo systemctl start colchuga-bot

# Остановка
sudo systemctl stop colchuga-bot

# Перезапуск
sudo systemctl restart colchuga-bot

# Просмотр логов
sudo journalctl -u colchuga-bot -f

# Последние 100 строк логов
sudo journalctl -u colchuga-bot -n 100
```

### Обновление проекта

```bash
cd ~/projects/colchuga_bot

# Остановка бота
sudo systemctl stop colchuga-bot

# Обновление кода (если через git)
git pull

# Активация виртуального окружения
source venv/bin/activate

# Обновление зависимостей (если requirements.txt изменился)
pip install -r requirements.txt

# Применение новых миграций (если есть)
alembic upgrade head

# Запуск бота
sudo systemctl start colchuga-bot
```

### Резервное копирование базы данных

```bash
# Создание бэкапа
sudo -u postgres pg_dump giveaway_bot > ~/backup_$(date +%Y%m%d_%H%M%S).sql

# Восстановление из бэкапа
sudo -u postgres psql giveaway_bot < ~/backup_YYYYMMDD_HHMMSS.sql
```

### Доступ к базе данных

```bash
sudo -u postgres psql giveaway_bot
```

---

## Решение проблем

### Бот не запускается

```bash
# Проверьте логи
sudo journalctl -u colchuga-bot -n 50

# Проверьте конфигурацию .env
cat .env

# Проверьте подключение к базе данных
sudo -u postgres psql -U bot_user -d giveaway_bot -c "SELECT 1;"
```

### Ошибка подключения к базе данных

```bash
# Проверьте, что PostgreSQL запущен
sudo systemctl status postgresql

# Проверьте права доступа
sudo -u postgres psql -c "\du"

# Проверьте DATABASE_URL в .env
grep DATABASE_URL .env
```

### Ошибка импорта модулей

```bash
# Убедитесь, что виртуальное окружение активировано
source venv/bin/activate

# Переустановите зависимости
pip install -r requirements.txt
```

---

## Размер установки

- Python 3.11: ~50 MB
- PostgreSQL: ~150 MB
- Зависимости Python: ~100 MB
- Итого: ~300 MB (вместо нескольких GB для Docker)

---

## Безопасность

1. **Никогда не коммитьте `.env` файл в Git**
2. **Используйте надежные пароли** для базы данных
3. **Ограничьте доступ к серверу**:
   ```bash
   # Установка fail2ban
   apt install fail2ban
   
   # Ограничение SSH (опционально)
   # Отредактируйте /etc/ssh/sshd_config
   ```
4. **Регулярно обновляйте систему**:
   ```bash
   apt update && apt upgrade -y
   ```

---

## Преимущества этого подхода

✅ **Меньше места** - нет Docker образов (экономия ~2-3 GB)  
✅ **Проще управление** - обычные команды systemctl  
✅ **Быстрее запуск** - нет сборки образов  
✅ **Меньше зависимостей** - только Python и PostgreSQL  
✅ **Проще отладка** - прямые логи в journalctl  

---

## Что дальше?

После успешного запуска:
1. Проверьте, что бот отвечает в Telegram
2. Протестируйте все команды бота
3. Настройте автоматическое резервное копирование (cron)
4. Мониторьте логи: `sudo journalctl -u colchuga-bot -f`
