"""Admin-only command handlers."""

from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.stdlib import BoundLogger

from app.config import Settings
from app.services.admin_service import (
    broadcast_to_all_users,
    collect_admin_stats,
    export_users_csv,
    format_stats_message,
)

router = Router(name=__name__)


def is_admin_user(user_id: int | None, admin_ids: tuple[int, ...]) -> bool:
    return user_id is not None and user_id in admin_ids


async def reject_if_not_admin(message: Message, settings: Settings) -> bool:
    user_id = message.from_user.id if message.from_user else None
    if is_admin_user(user_id, settings.admin_ids):
        return False

    await message.answer("This command is available only to admins.")
    return True


@router.message(Command("stats"))
async def handle_stats(
    message: Message,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    app_logger: BoundLogger,
) -> None:
    if await reject_if_not_admin(message, settings):
        return

    stats = await collect_admin_stats(session_factory)
    app_logger.info("admin_command_used", command="stats", admin_id=message.from_user.id)
    await message.answer(format_stats_message(stats))


@router.message(Command("export"))
async def handle_export(
    message: Message,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    app_logger: BoundLogger,
) -> None:
    if await reject_if_not_admin(message, settings):
        return

    csv_bytes = await export_users_csv(session_factory)
    filename = f"giveaway_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    file = BufferedInputFile(csv_bytes, filename=filename)
    app_logger.info("admin_command_used", command="export", admin_id=message.from_user.id)
    await message.answer_document(document=file)


@router.message(Command("broadcast"))
async def handle_broadcast(
    message: Message,
    bot: Bot,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    app_logger: BoundLogger,
) -> None:
    if await reject_if_not_admin(message, settings):
        return

    text = (message.text or "").strip()
    _, _, payload = text.partition(" ")
    payload = payload.strip()

    if not payload:
        await message.answer("Usage: /broadcast <message>")
        return

    app_logger.info("admin_command_used", command="broadcast", admin_id=message.from_user.id)
    await message.answer("Broadcast started.")

    result = await broadcast_to_all_users(
        bot=bot,
        session_factory=session_factory,
        message_text=payload,
        logger=app_logger,
    )

    await message.answer(
        "Broadcast complete.\n"
        f"Delivered: {result.delivered}\n"
        f"Failed: {result.failed}"
    )
