"""Bot inline keyboards."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import CHECK_SUBSCRIPTION_CALLBACK


def build_subscription_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Открыть канал", url=channel_url)],
            [
                InlineKeyboardButton(
                    text="Проверить подписку",
                    callback_data=CHECK_SUBSCRIPTION_CALLBACK,
                )
            ],
        ]
    )
