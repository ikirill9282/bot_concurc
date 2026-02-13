#!/usr/bin/env python3
"""Скрипт для синхронизации существующих данных из БД в Google Sheets."""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.db.session import create_engine_and_session_factory
from app.logging_setup import configure_logging, get_logger
from app.repositories.users import UsersRepository
from app.services.google_sheets_service import GoogleSheetsService


async def sync_all_users_to_sheets():
    """Синхронизировать всех пользователей из БД в Google Sheets."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("sync_to_sheets")

    if not settings.google_sheets_enabled:
        logger.error("Google Sheets integration is disabled. Set GOOGLE_SHEETS_ENABLED=true")
        return

    google_sheets_service = GoogleSheetsService(settings, logger)

    if not google_sheets_service.is_enabled():
        logger.error("Google Sheets service is not properly configured")
        return

    engine, session_factory = create_engine_and_session_factory(settings.database_url)

    try:
        async with session_factory() as session:
            # Получаем всех пользователей через репозиторий
            from sqlalchemy import select
            from app.db.models import User
            
            stmt = select(User)
            result = await session.execute(stmt)
            users = result.scalars().all()

            logger.info(f"Found {len(users)} users to sync")

            synced = 0
            failed = 0

            for user in users:
                success = google_sheets_service.add_contact(
                    tg_user_id=user.tg_user_id,
                    username=user.username,
                    telegram_first_name=user.first_name,
                    telegram_last_name=user.last_name,
                    contact_name=user.contact_name,
                    contact_phone=user.contact_phone,
                    contact_email=user.contact_email,
                    is_subscribed=user.is_subscribed,
                    is_participant=user.is_participant,
                    referrals_confirmed=user.referrals_confirmed or 0,
                )

                if success:
                    synced += 1
                    logger.info(f"Synced user {user.tg_user_id}")
                else:
                    failed += 1
                    logger.warning(f"Failed to sync user {user.tg_user_id}")

            logger.info(f"Sync complete: {synced} synced, {failed} failed")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(sync_all_users_to_sheets())
