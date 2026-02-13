"""Bot inline keyboards."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from app.bot.callbacks import CHECK_SUBSCRIPTION_CALLBACK, REQUEST_CONTACT_CALLBACK


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


def build_contact_request_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса контактной информации."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📱 Отправить контакт", request_contact=True),
            ],
            [
                KeyboardButton(text="✏️ Ввести вручную"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def build_simple_contact_keyboard() -> ReplyKeyboardMarkup:
    """Простая клавиатура только с кнопкой отправки контакта."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📱 Отправить контакт", request_contact=True),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def build_contact_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отмены ввода контактов."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="❌ Отменить"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def build_remove_keyboard() -> ReplyKeyboardMarkup:
    """Удаляет клавиатуру."""
    return ReplyKeyboardMarkup(keyboard=[], resize_keyboard=True)
