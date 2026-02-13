# Настройка интеграции с Google Sheets

## Описание

Бот автоматически сохраняет контактную информацию пользователей в Google таблицу при получении контактов.

## Шаги настройки

### 1. Создание Google Cloud проекта и Service Account

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API:
   - Перейдите в "APIs & Services" > "Library"
   - Найдите "Google Sheets API" и включите его
   - Также включите "Google Drive API"

### 2. Создание Service Account

1. Перейдите в "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "Service Account"
3. Заполните данные:
   - Service account name: `colchuga-bot-sheets`
   - Service account ID: `colchuga-bot-sheets` (автоматически)
   - Description: `Service account for Colchuga Bot Google Sheets integration`
4. Нажмите "Create and Continue"
5. Пропустите шаг "Grant this service account access to project" (нажмите "Continue")
6. Нажмите "Done"

### 3. Создание ключа для Service Account

1. Найдите созданный Service Account в списке
2. Откройте его и перейдите на вкладку "Keys"
3. Нажмите "Add Key" > "Create new key"
4. Выберите формат JSON
5. Нажмите "Create"
6. Файл с ключом будет автоматически скачан

### 4. Настройка доступа к Google таблице

1. Создайте новую Google таблицу или откройте существующую
2. Скопируйте ID таблицы из URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
   ```
   Где `SPREADSHEET_ID` - это ID вашей таблицы
3. Поделитесь таблицей с email адресом Service Account:
   - Откройте настройки доступа к таблице (кнопка "Share")
   - Добавьте email адрес из скачанного JSON файла (поле `client_email`)
   - Дайте права "Editor" (Редактор)

### 5. Настройка бота

1. Переместите скачанный JSON файл с ключами в директорию проекта:
   ```bash
   cp ~/Downloads/your-project-xxxxx.json ./google_credentials.json
   ```

2. Обновите файл `.env`:
   ```env
   GOOGLE_SHEETS_ENABLED=true
   GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
   GOOGLE_SHEETS_WORKSHEET_NAME=Контакты
   GOOGLE_SHEETS_CREDENTIALS_PATH=./google_credentials.json
   ```

3. Если используете Docker, убедитесь что файл `google_credentials.json` доступен в контейнере:
   - Добавьте файл в директорию проекта
   - Или смонтируйте его как volume в `docker-compose.yml`

### 6. Структура таблицы

Бот автоматически создаст лист с названием из `GOOGLE_SHEETS_WORKSHEET_NAME` (по умолчанию "Контакты") и добавит заголовки:

| Дата | Telegram ID | Username | Имя (Telegram) | Имя (контакт) | Телефон | Email | Подписан | Участник | Рефералов подтверждено |
|------|-------------|----------|----------------|---------------|---------|-------|----------|----------|------------------------|
| ...  | ...         | ...      | ...            | ...           | ...     | ...   | ...      | ...      | ...                    |

### 7. Проверка работы

1. Перезапустите бота:
   ```bash
   docker compose restart bot
   ```

2. Проверьте логи:
   ```bash
   docker compose logs bot | grep google_sheets
   ```

3. Должно появиться сообщение:
   ```
   google_sheets_client_initialized
   ```

4. Протестируйте бота - отправьте контакт через бота и проверьте таблицу

## Отключение интеграции

Чтобы отключить интеграцию с Google Sheets, установите в `.env`:
```env
GOOGLE_SHEETS_ENABLED=false
```

## Безопасность

⚠️ **ВАЖНО:**
- Никогда не коммитьте файл `google_credentials.json` в Git!
- Добавьте его в `.gitignore`:
  ```
  google_credentials.json
  *.json
  ```
- Храните файл с ключами в безопасном месте
- Не передавайте файл с ключами третьим лицам

## Troubleshooting

### Ошибка: "google_sheets_credentials_file_not_found"
- Убедитесь, что путь к файлу указан правильно в `GOOGLE_SHEETS_CREDENTIALS_PATH`
- Проверьте, что файл существует и доступен для чтения

### Ошибка: "google_sheets_spreadsheet_id_not_set"
- Убедитесь, что `GOOGLE_SHEETS_SPREADSHEET_ID` указан в `.env`
- Проверьте правильность ID таблицы

### Ошибка доступа к таблице
- Убедитесь, что Service Account email добавлен в список редакторов таблицы
- Проверьте, что таблица не удалена и доступна

### Данные не появляются в таблице
- Проверьте логи бота на наличие ошибок
- Убедитесь, что `GOOGLE_SHEETS_ENABLED=true`
- Проверьте права доступа Service Account к таблице
