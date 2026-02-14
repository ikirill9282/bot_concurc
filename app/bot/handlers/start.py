"""/start command handler."""

from __future__ import annotations

from pathlib import Path

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.stdlib import BoundLogger

from app.bot.keyboards import build_subscription_keyboard
from app.services.referral_service import process_start_command

router = Router(name=__name__)
WELCOME_IMAGE_PATH = Path(__file__).resolve().parents[2] / "assets" / "23 ПРИЗА (2).png"


@router.message(CommandStart())
async def handle_start(
    message: Message,
    command: CommandObject | None,
    session_factory: async_sessionmaker[AsyncSession],
    app_logger: BoundLogger,
    bot_username: str,
    channel_url: str,
) -> None:
    if message.from_user is None:
        return

    start_argument = command.args if command else None

    result = await process_start_command(
        session_factory=session_factory,
        telegram_user=message.from_user,
        start_argument=start_argument,
        logger=app_logger,
    )

    referral_link = f"https://t.me/{bot_username}?start={result.tg_user_id}" if bot_username else ""

    parts = [
        "Привет! Чтобы участвовать в розыгрыше, выполните условия:",
        "1) Подпишитесь на канал.",
        "2) Нажмите «Проверить подписку».",
        "3) Отправьте свои контакты (имя и телефон).",
        "4) Отправьте другу вашу личную ссылку и попросите подписаться на канал.",
        "5) Как только друг подпишется, вы получите уведомление и станете участником розыгрыша.",
    ]

    if referral_link:
        parts.append(f"Ваша ссылка для приглашения:\n{referral_link}")

    if result.referral_applied:
        parts.append("Реферальный код принят. Подтвердите подписку кнопкой ниже.")

    response_text = "\n".join(parts)
    keyboard = build_subscription_keyboard(channel_url)

    if WELCOME_IMAGE_PATH.exists():
        await message.answer_photo(
            photo=FSInputFile(str(WELCOME_IMAGE_PATH)),
            caption=response_text,
            reply_markup=keyboard,
        )
        return

    app_logger.warning("welcome_image_not_found", path=str(WELCOME_IMAGE_PATH))
    await message.answer(response_text, reply_markup=keyboard)
