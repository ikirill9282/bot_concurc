"""Contact information collection handlers."""

from __future__ import annotations

import re

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Contact, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.stdlib import BoundLogger

from app.bot.callbacks import REQUEST_CONTACT_CALLBACK
from app.bot.keyboards import (
    build_contact_cancel_keyboard,
    build_contact_request_keyboard,
    build_remove_keyboard,
    build_simple_contact_keyboard,
)
from app.repositories.users import UsersRepository
from app.services.google_sheets_service import GoogleSheetsService


async def _sync_to_sheets_async(
    google_sheets_service: GoogleSheetsService,
    tg_user_id: int,
    username: str | None,
    telegram_first_name: str | None,
    telegram_last_name: str | None,
    contact_name: str | None,
    contact_phone: str | None,
    is_subscribed: bool,
    is_participant: bool,
    referrals_confirmed: int,
    logger: BoundLogger,
) -> None:
    """Асинхронная обертка для синхронизации в Google Sheets."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: google_sheets_service.add_contact(
            tg_user_id=tg_user_id,
            username=username,
            telegram_first_name=telegram_first_name,
            telegram_last_name=telegram_last_name,
            contact_name=contact_name,
            contact_phone=contact_phone,
            is_subscribed=is_subscribed,
            is_participant=is_participant,
            referrals_confirmed=referrals_confirmed,
        ),
    )
    logger.info("contact_synced_to_sheets", tg_user_id=tg_user_id)


class ContactStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_simple_contact = State()  # Простой запрос контакта после подписки


router = Router(name=__name__)


def validate_phone(phone: str) -> bool:
    """Валидация телефона (российский формат)."""
    # Удаляем все нецифровые символы кроме +
    cleaned = re.sub(r"[^\d+]", "", phone)
    # Проверяем формат: +7XXXXXXXXXX или 8XXXXXXXXXX или 7XXXXXXXXXX
    pattern = r"^(\+?7|8)?\d{10}$"
    return bool(re.match(pattern, cleaned))


@router.callback_query(F.data == REQUEST_CONTACT_CALLBACK)
async def handle_request_contact_callback(
    callback: CallbackQuery,
    state: FSMContext,
    app_logger: BoundLogger,
) -> None:
    """Обработчик кнопки запроса контактной информации."""
    if callback.from_user is None:
        await callback.answer()
        return

    await callback.answer()
    await state.set_state(ContactStates.waiting_for_name)

    text = (
        "Для участия в розыгрыше необходимо предоставить контактную информацию:\n\n"
        "1️⃣ Введите ваше полное имя (ФИО)"
    )

    if callback.message:
        try:
            await callback.message.edit_text(text)
        except Exception:
            await callback.message.answer(text, reply_markup=build_contact_cancel_keyboard())
    else:
        await callback.message.answer(text, reply_markup=build_contact_cancel_keyboard())


async def request_contact_info(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    app_logger: BoundLogger,
) -> None:
    """Запросить контактную информацию у пользователя."""
    await state.set_state(ContactStates.waiting_for_name)
    text = (
        "Для участия в розыгрыше необходимо предоставить контактную информацию:\n\n"
        "1️⃣ Введите ваше полное имя (ФИО)"
    )
    await bot.send_message(chat_id, text, reply_markup=build_contact_cancel_keyboard())


async def request_simple_contact(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    app_logger: BoundLogger,
) -> None:
    """Запросить контакт через кнопку Telegram (простой вариант после подписки)."""
    await state.set_state(ContactStates.waiting_for_simple_contact)
    text = "Спасибо, подписка подтверждена.\n\nТеперь отправьте свои контакты:"
    await bot.send_message(chat_id, text, reply_markup=build_simple_contact_keyboard())


@router.message(Command("contact"))
async def handle_contact_command(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
    app_logger: BoundLogger,
) -> None:
    """Обработчик команды /contact для запроса контактной информации."""
    if message.from_user is None:
        return

    # Проверяем, является ли пользователь участником
    async with session_factory() as session:
        user = await UsersRepository.get_by_tg_user_id(session, message.from_user.id)
        if user is None:
            await message.answer(
                "Сначала выполните условия участия в розыгрыше.\n"
                "Используйте команду /start для начала."
            )
            return

        if not user.is_participant:
            await message.answer(
                "Вы еще не являетесь участником розыгрыша.\n"
                "Выполните все условия участия, чтобы получить возможность предоставить контактную информацию."
            )
            return

        # Если контактная информация уже предоставлена
        if user.contact_name and user.contact_phone:
            await message.answer(
                f"✅ Ваша контактная информация уже сохранена:\n\n"
                f"Имя: {user.contact_name}\n"
                f"Телефон: {user.contact_phone}\n\n"
                "Если хотите изменить данные, начните заново."
            )
            return

    # Запрашиваем контактную информацию
    await request_contact_info(message.bot, message.from_user.id, state, app_logger)


@router.message(StateFilter(ContactStates.waiting_for_name), F.text)
async def handle_contact_name(
    message: Message,
    state: FSMContext,
    app_logger: BoundLogger,
) -> None:
    """Обработка ввода имени."""
    if message.text is None:
        return

    if message.text.strip().lower() in ["отменить", "❌ отменить", "cancel"]:
        await state.clear()
        await message.answer("Ввод контактной информации отменен.", reply_markup=build_remove_keyboard())
        return

    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Пожалуйста, введите полное имя (минимум 2 символа).")
        return

    await state.update_data(contact_name=name)
    await state.set_state(ContactStates.waiting_for_phone)

    await message.answer(
        f"✅ Имя сохранено: {name}\n\n"
        "2️⃣ Теперь введите ваш номер телефона\n"
        "Формат: +7XXXXXXXXXX или 8XXXXXXXXXX",
        reply_markup=build_contact_cancel_keyboard(),
    )


@router.message(F.contact)
async def handle_contact_from_button(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
    bot: Bot,
    bot_username: str,
    app_logger: BoundLogger,
    google_sheets_service: GoogleSheetsService,
) -> None:
    """Обработка контакта из кнопки Telegram.
    
    Это событие срабатывает ТОЛЬКО после того, как пользователь нажал "OK" 
    в диалоге подтверждения отправки контакта.
    """
    if message.contact is None or message.from_user is None:
        return

    current_state = await state.get_state()
    contact: Contact = message.contact
    
    # Проверяем, что контакт действительно был отправлен пользователем
    # (user_id должен совпадать с отправителем сообщения)
    if contact.user_id is not None and contact.user_id != message.from_user.id:
        app_logger.warning(
            "contact_user_id_mismatch",
            contact_user_id=contact.user_id,
            message_user_id=message.from_user.id,
        )
        # Продолжаем обработку, так как это может быть контакт другого пользователя
    
    phone = contact.phone_number
    name = contact.first_name or ""
    if contact.last_name:
        name = f"{name} {contact.last_name}".strip()

    # Валидация: проверяем, что есть телефон
    if not phone:
        app_logger.warning("contact_received_without_phone", tg_user_id=message.from_user.id)
        await message.answer("Не удалось получить номер телефона. Попробуйте еще раз.")
        return

    # Нормализуем телефон
    cleaned_phone = re.sub(r"[^\d+]", "", phone)
    if cleaned_phone.startswith("8"):
        cleaned_phone = "+7" + cleaned_phone[1:]
    elif not cleaned_phone.startswith("+7"):
        cleaned_phone = "+7" + cleaned_phone

    app_logger.info(
        "contact_received_from_user",
        tg_user_id=message.from_user.id,
        has_name=bool(name),
        has_phone=bool(cleaned_phone),
        state=str(current_state),
    )

    # Если это простой запрос контакта после подписки
    if current_state == ContactStates.waiting_for_simple_contact:
        # Сохраняем контакт в базу данных
        async with session_factory() as session:
            async with session.begin():
                user = await UsersRepository.get_by_tg_user_id(session, message.from_user.id, for_update=True)
                if user is not None:
                    user.contact_name = name
                    user.contact_phone = cleaned_phone
                    app_logger.info(
                        "contact_saved_to_db",
                        tg_user_id=message.from_user.id,
                        has_name=bool(name),
                        has_phone=bool(cleaned_phone),
                    )
            
            # Сохраняем в Google Sheets ТОЛЬКО после успешного сохранения в БД
            # и ТОЛЬКО если есть имя и телефон
            if user is not None and name and cleaned_phone:
                app_logger.info(
                    "syncing_contact_to_sheets",
                    tg_user_id=user.tg_user_id,
                )
                import asyncio
                asyncio.create_task(
                    _sync_to_sheets_async(
                        google_sheets_service,
                        user.tg_user_id,
                        user.username,
                        user.first_name,
                        user.last_name,
                        name,
                        cleaned_phone,
                        user.is_subscribed,
                        user.is_participant,
                        user.referrals_confirmed,
                        app_logger,
                    )
                )

        await state.clear()
        referral_link = f"https://t.me/{bot_username}?start={message.from_user.id}" if bot_username else ""
        
        response = (
            "✅ Контакт получен!\n\n"
            "Теперь отправьте другу вашу ссылку и попросите подписаться.\n"
            "Как только друг подпишется, вы станете участником розыгрыша."
        )
        if referral_link:
            response += f"\n\nВаша ссылка:\n{referral_link}"

        await message.answer(response, reply_markup=build_remove_keyboard())
        return

    # Если это полный процесс ввода контактной информации (не используется, но оставляем для совместимости)
    if current_state in [ContactStates.waiting_for_name, ContactStates.waiting_for_phone]:
        # Сохраняем контакт
        async with session_factory() as session:
            async with session.begin():
                user = await UsersRepository.get_by_tg_user_id(session, message.from_user.id, for_update=True)
                if user is not None:
                    user.contact_name = name
                    user.contact_phone = cleaned_phone
            
            # Сохраняем в Google Sheets
            if user is not None:
                    import asyncio
                    asyncio.create_task(
                        _sync_to_sheets_async(
                            google_sheets_service,
                            user.tg_user_id,
                            user.username,
                            user.first_name,
                            user.last_name,
                            name,
                            cleaned_phone,
                            user.is_subscribed,
                            user.is_participant,
                            user.referrals_confirmed,
                            app_logger,
                        )
                    )
        
        await state.clear()
        referral_link = f"https://t.me/{bot_username}?start={message.from_user.id}" if bot_username else ""
        
        response = (
            "✅ Контакт получен!\n\n"
            "Теперь отправьте другу вашу ссылку и попросите подписаться.\n"
            "Как только друг подпишется, вы станете участником розыгрыша."
        )
        if referral_link:
            response += f"\n\nВаша ссылка:\n{referral_link}"
        
        await message.answer(response, reply_markup=build_remove_keyboard())


@router.message(StateFilter(ContactStates.waiting_for_phone), F.text)
async def handle_contact_phone(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker[AsyncSession],
    bot: Bot,
    bot_username: str,
    app_logger: BoundLogger,
    google_sheets_service: GoogleSheetsService,
) -> None:
    """Обработка ввода телефона."""
    if message.text is None or message.from_user is None:
        return

    if message.text.strip().lower() in ["отменить", "❌ отменить", "cancel"]:
        await state.clear()
        await message.answer("Ввод контактной информации отменен.", reply_markup=build_remove_keyboard())
        return

    phone = message.text.strip()
    if not validate_phone(phone):
        await message.answer(
            "Неверный формат телефона. Пожалуйста, введите номер в формате:\n"
            "+7XXXXXXXXXX или 8XXXXXXXXXX"
        )
        return

    # Нормализуем телефон
    cleaned_phone = re.sub(r"[^\d+]", "", phone)
    if cleaned_phone.startswith("8"):
        cleaned_phone = "+7" + cleaned_phone[1:]
    elif not cleaned_phone.startswith("+7"):
        cleaned_phone = "+7" + cleaned_phone

    data = await state.get_data()
    contact_name = data.get("contact_name", "")

    # Сохраняем контактную информацию в базу данных
    async with session_factory() as session:
        async with session.begin():
            user = await UsersRepository.get_by_tg_user_id(session, message.from_user.id, for_update=True)
            if user is not None:
                user.contact_name = contact_name
                user.contact_phone = cleaned_phone
                app_logger.info(
                    "contact_info_saved",
                    tg_user_id=message.from_user.id,
                    has_name=bool(contact_name),
                    has_phone=bool(cleaned_phone),
                )
        
        # Сохраняем в Google Sheets после коммита транзакции (асинхронно в фоне)
        if user is not None:
            import asyncio
            asyncio.create_task(
                _sync_to_sheets_async(
                    google_sheets_service,
                    user.tg_user_id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    contact_name,
                    cleaned_phone,
                    user.is_subscribed,
                    user.is_participant,
                    user.referrals_confirmed,
                    app_logger,
                )
            )

    await state.clear()
    referral_link = f"https://t.me/{bot_username}?start={message.from_user.id}" if bot_username else ""
    
    response = (
        "✅ Контактная информация сохранена!\n\n"
        f"Имя: {contact_name}\n"
        f"Телефон: {cleaned_phone}\n\n"
        "Теперь отправьте другу вашу ссылку и попросите подписаться.\n"
        "Как только друг подпишется, вы станете участником розыгрыша."
    )
    if referral_link:
        response += f"\n\nВаша ссылка:\n{referral_link}"

    await message.answer(response, reply_markup=build_remove_keyboard())


