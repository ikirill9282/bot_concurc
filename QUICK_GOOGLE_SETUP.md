# Быстрая настройка Google Sheets

## Проблема
Таблица пуста, потому что отсутствует файл `google_credentials.json`.

## Решение за 5 минут

### Шаг 1: Создайте Service Account в Google Cloud

1. Откройте https://console.cloud.google.com/
2. Создайте проект (или выберите существующий)
3. Включите API:
   - Google Sheets API
   - Google Drive API
4. Перейдите в "Credentials" > "Create Credentials" > "Service Account"
5. Создайте Service Account
6. Перейдите в "Keys" > "Add Key" > "Create new key" > JSON
7. Скачайте JSON файл

### Шаг 2: Настройте доступ к таблице

1. Откройте вашу Google таблицу
2. Скопируйте ID из URL: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
3. Нажмите "Share" (Поделиться)
4. Добавьте email из JSON файла (поле `client_email`)
5. Дайте права "Editor"

### Шаг 3: Добавьте файл в проект

1. Переименуйте скачанный JSON файл в `google_credentials.json`
2. Поместите его в корень проекта: `/Users/kirill9282/Downloads/!!!!!!!!!!!!Project/new/colchuga_bot/`
3. Обновите `.env`:
   ```env
   GOOGLE_SHEETS_ENABLED=true
   GOOGLE_SHEETS_SPREADSHEET_ID=ваш_id_таблицы
   GOOGLE_SHEETS_WORKSHEET_NAME=Лист1
   GOOGLE_SHEETS_CREDENTIALS_PATH=./google_credentials.json
   ```

### Шаг 4: Перезапустите бота

```bash
docker compose restart bot
```

### Шаг 5: Проверьте

1. Отправьте контакт через бота
2. Проверьте таблицу - данные должны появиться автоматически

## Важно!

- Файл `google_credentials.json` содержит секретные ключи
- НЕ коммитьте его в Git (уже добавлен в .gitignore)
- Храните файл в безопасном месте
