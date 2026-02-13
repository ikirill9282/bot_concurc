"""Google Sheets integration service."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from structlog.stdlib import BoundLogger

from app.config import Settings


class GoogleSheetsService:
    """Service for interacting with Google Sheets."""

    def __init__(self, settings: Settings, logger: BoundLogger) -> None:
        self.settings = settings
        self.logger = logger
        self.client: gspread.Client | None = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Google Sheets client."""
        if not self.settings.google_sheets_enabled:
            self.logger.info("google_sheets_disabled")
            return

        if not self.settings.google_sheets_spreadsheet_id:
            self.logger.warning("google_sheets_spreadsheet_id_not_set")
            return

        if not self.settings.google_sheets_credentials_path:
            self.logger.warning("google_sheets_credentials_path_not_set")
            return

        try:
            credentials_path = Path(self.settings.google_sheets_credentials_path)
            if not credentials_path.exists():
                self.logger.error(
                    "google_sheets_credentials_file_not_found",
                    path=str(credentials_path),
                )
                return

            # Загружаем credentials из JSON файла
            with open(credentials_path, "r", encoding="utf-8") as f:
                credentials_data = json.load(f)

            credentials = Credentials.from_service_account_info(
                credentials_data,
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive",
                ],
            )

            self.client = gspread.authorize(credentials)
            self.logger.info("google_sheets_client_initialized")
        except Exception as e:
            self.logger.exception("google_sheets_client_init_error", error=str(e))
            self.client = None

    def is_enabled(self) -> bool:
        """Check if Google Sheets integration is enabled and configured."""
        return (
            self.settings.google_sheets_enabled
            and self.client is not None
            and self.settings.google_sheets_spreadsheet_id is not None
        )

    def _get_worksheet(self) -> gspread.Worksheet | None:
        """Get worksheet by name or create if not exists."""
        if not self.is_enabled() or self.client is None:
            return None

        try:
            spreadsheet = self.client.open_by_key(self.settings.google_sheets_spreadsheet_id)
            try:
                worksheet = spreadsheet.worksheet(self.settings.google_sheets_worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                # Создаем новый лист если не существует
                worksheet = spreadsheet.add_worksheet(
                    title=self.settings.google_sheets_worksheet_name,
                    rows=1000,
                    cols=10,
                )
                # Добавляем заголовки
                worksheet.append_row(
                    [
                        "№",
                        "Дата",
                        "Telegram ID",
                        "Username",
                        "Имя (Telegram)",
                        "Имя (контакт)",
                        "Телефон",
                        "Подписан",
                        "Участник",
                        "Рефералов подтверждено",
                    ]
                )
                self.logger.info("google_sheets_worksheet_created", name=self.settings.google_sheets_worksheet_name)

            return worksheet
        except Exception as e:
            self.logger.exception("google_sheets_get_worksheet_error", error=str(e))
            return None

    def add_contact(
        self,
        tg_user_id: int,
        username: str | None,
        telegram_first_name: str | None,
        telegram_last_name: str | None,
        contact_name: str | None,
        contact_phone: str | None,
        is_subscribed: bool = False,
        is_participant: bool = False,
        referrals_confirmed: int = 0,
    ) -> bool:
        """Add or update contact information in Google Sheets."""
        if not self.is_enabled():
            return False

        # Не создаем запись в Google Sheets без контактной информации
        if not contact_name or not contact_phone:
            self.logger.debug(
                "skipping_sheets_update_no_contact",
                tg_user_id=tg_user_id,
                has_name=bool(contact_name),
                has_phone=bool(contact_phone),
            )
            return False

        worksheet = self._get_worksheet()
        if worksheet is None:
            return False

        try:
            # Оптимизированный поиск: используем find для поиска по колонке C (Telegram ID)
            try:
                # Ищем Telegram ID в колонке C (индекс 3 в gspread, так как индексация с 1)
                cell = worksheet.find(str(tg_user_id), in_column=3)
                row_index = cell.row if cell else None
            except gspread.exceptions.CellNotFound:
                row_index = None
            
            # Если не нашли через find, используем get_all_values (медленнее, но надежнее)
            if row_index is None:
                all_values = worksheet.get_all_values()
                if len(all_values) > 1:
                    for idx, row in enumerate(all_values[1:], start=2):
                        if len(row) > 2 and row[2] == str(tg_user_id):
                            row_index = idx
                            break

            # Формируем имя из Telegram
            telegram_name = ""
            if telegram_first_name:
                telegram_name = telegram_first_name
                if telegram_last_name:
                    telegram_name = f"{telegram_first_name} {telegram_last_name}"

            # Форматируем дату
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Определяем порядковый номер
            if row_index is not None:
                # При обновлении существующей записи сохраняем номер из первой колонки
                existing_row = worksheet.row_values(row_index)
                serial_number = existing_row[0] if len(existing_row) > 0 and existing_row[0].isdigit() else str(row_index - 1)
            else:
                # Для новой записи берем следующий номер (используем быстрый способ)
                try:
                    # Получаем только первую колонку для подсчета
                    col_a_values = worksheet.col_values(1)
                    if len(col_a_values) <= 1:  # Только заголовок
                        serial_number = "1"
                    else:
                        max_num = 0
                        for val in col_a_values[1:]:  # Пропускаем заголовок
                            if val.isdigit():
                                max_num = max(max_num, int(val))
                        serial_number = str(max_num + 1)
                except Exception:
                    # Fallback на старый способ
                    all_values = worksheet.get_all_values()
                    if len(all_values) <= 1:
                        serial_number = "1"
                    else:
                        max_num = 0
                        for row in all_values[1:]:
                            if len(row) > 0 and row[0].isdigit():
                                try:
                                    max_num = max(max_num, int(row[0]))
                                except ValueError:
                                    pass
                        serial_number = str(max_num + 1)

            row = [
                serial_number,
                current_date,
                str(tg_user_id),
                username or "",
                telegram_name,
                contact_name or "",
                contact_phone or "",
                "Да" if is_subscribed else "Нет",
                "Да" if is_participant else "Нет",
                str(referrals_confirmed),
            ]

            if row_index is not None:
                # Обновляем существующую строку используя batch update (быстрее)
                range_name = f"{row_index}:{row_index}"
                worksheet.update(range_name, [row], value_input_option="USER_ENTERED")
                self.logger.info(
                    "contact_updated_in_sheets",
                    tg_user_id=tg_user_id,
                    row=row_index,
                )
            else:
                # Добавляем новую строку
                worksheet.append_row(row, value_input_option="USER_ENTERED")
                self.logger.info(
                    "contact_added_to_sheets",
                    tg_user_id=tg_user_id,
                    has_contact_name=bool(contact_name),
                    has_contact_phone=bool(contact_phone),
                )
            return True
        except Exception as e:
            self.logger.exception("google_sheets_add_contact_error", tg_user_id=tg_user_id, error=str(e))
            return False

    def update_contact(
        self,
        tg_user_id: int,
        contact_name: str | None = None,
        contact_phone: str | None = None,
        is_subscribed: bool | None = None,
        is_participant: bool | None = None,
        referrals_confirmed: int | None = None,
    ) -> bool:
        """Update existing contact in Google Sheets."""
        if not self.is_enabled():
            return False

        worksheet = self._get_worksheet()
        if worksheet is None:
            return False

        try:
            # Находим строку с данным пользователем
            all_values = worksheet.get_all_values()
            if not all_values:
                return False

            # Пропускаем заголовок
            for idx, row in enumerate(all_values[1:], start=2):
                # Telegram ID теперь во второй колонке (индекс 2)
                if len(row) > 2 and row[2] == str(tg_user_id):
                    # Обновляем значения (с учетом новой первой колонки с номером)
                    if contact_name is not None and len(row) > 5:
                        worksheet.update_cell(idx, 6, contact_name)
                    if contact_phone is not None and len(row) > 6:
                        worksheet.update_cell(idx, 7, contact_phone)
                    if is_subscribed is not None and len(row) > 7:
                        worksheet.update_cell(idx, 8, "Да" if is_subscribed else "Нет")
                    if is_participant is not None and len(row) > 8:
                        worksheet.update_cell(idx, 9, "Да" if is_participant else "Нет")
                    if referrals_confirmed is not None and len(row) > 9:
                        worksheet.update_cell(idx, 10, str(referrals_confirmed))

                    self.logger.info("contact_updated_in_sheets", tg_user_id=tg_user_id)
                    return True

            # Если не нашли - добавляем новую запись
            self.logger.warning("contact_not_found_in_sheets_for_update", tg_user_id=tg_user_id)
            return False
        except Exception as e:
            self.logger.exception("google_sheets_update_contact_error", tg_user_id=tg_user_id, error=str(e))
            return False
