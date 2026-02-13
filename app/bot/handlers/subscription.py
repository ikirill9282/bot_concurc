"""Subscription verification callbacks."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.stdlib import BoundLogger

from aiogram.fsm.context import FSMContext

from app.bot.callbacks import CHECK_SUBSCRIPTION_CALLBACK, REQUEST_CONTACT_CALLBACK
from app.bot.handlers.contact import request_contact_info, request_simple_contact
from app.bot.keyboards import build_subscription_keyboard
from app.constants import INVALID_SUBSCRIPTION_STATUSES, VALID_SUBSCRIPTION_STATUSES
from app.config import Settings
from app.repositories.users import UsersRepository
from app.services.google_sheets_service import GoogleSheetsService
from app.services.subscription_service import (
    SubscriptionConfirmationResult,
    confirm_subscription_and_referral,
    normalize_member_status,
    register_subscription_check_attempt,
)
from app.services.telegram_retry import run_with_retry

router = Router(name=__name__)


@router.callback_query(F.data == CHECK_SUBSCRIPTION_CALLBACK)
async def handle_check_subscription(
    callback: CallbackQuery,
    bot: Bot,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    app_logger: BoundLogger,
    bot_username: str,
    channel_url: str,
    state: FSMContext,
    google_sheets_service: GoogleSheetsService,
) -> None:
    if callback.from_user is None:
        await callback.answer()
        return

    retry_after = await register_subscription_check_attempt(
        session_factory=session_factory,
        telegram_user=callback.from_user,
        logger=app_logger,
    )

    if retry_after > 0:
        await callback.answer(
            f"Подождите {retry_after} сек. перед следующей проверкой.",
            show_alert=True,
        )
        return

    try:
        chat_member = await run_with_retry(
            bot.get_chat_member,
            chat_id=settings.channel_id,
            user_id=callback.from_user.id,
            logger=app_logger,
        )
    except TelegramAPIError:
        app_logger.exception("subscription_check_telegram_error", tg_user_id=callback.from_user.id)
        await callback.answer("Сейчас не удалось проверить подписку. Попробуйте чуть позже.", show_alert=True)
        return

    status = normalize_member_status(chat_member.status)
    is_subscribed = status in VALID_SUBSCRIPTION_STATUSES

    app_logger.info(
        "subscription_check_result",
        tg_user_id=callback.from_user.id,
        status=status,
        is_subscribed=is_subscribed,
    )

    if not is_subscribed:
        if status not in INVALID_SUBSCRIPTION_STATUSES:
            app_logger.warning(
                "subscription_check_unknown_status",
                tg_user_id=callback.from_user.id,
                status=status,
            )

        await callback.answer(
            "Подписка не подтверждена. Подпишитесь на канал и нажмите кнопку еще раз.",
            show_alert=True,
        )
        return

    confirmation_result: SubscriptionConfirmationResult = await confirm_subscription_and_referral(
        session_factory=session_factory,
        tg_user_id=callback.from_user.id,
        logger=app_logger,
    )

    if confirmation_result.referrer_to_notify is not None:
        # Обновляем Google Sheets для реферера (асинхронно в фоне) только если у него есть контакт
        async def _update_referrer_sheets():
            async with session_factory() as session:
                referrer = await UsersRepository.get_by_tg_user_id(session, confirmation_result.referrer_to_notify)
                # Обновляем Google Sheets только если у реферера есть контактная информация
                if referrer and referrer.contact_name and referrer.contact_phone:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: google_sheets_service.add_contact(
                            tg_user_id=referrer.tg_user_id,
                            username=referrer.username,
                            telegram_first_name=referrer.first_name,
                            telegram_last_name=referrer.last_name,
                            contact_name=referrer.contact_name,
                            contact_phone=referrer.contact_phone,
                            is_subscribed=referrer.is_subscribed,
                            is_participant=referrer.is_participant,
                            referrals_confirmed=referrer.referrals_confirmed,
                        ),
                    )
        import asyncio
        asyncio.create_task(_update_referrer_sheets())
        if confirmation_result.referrer_is_participant:
            referrer_text = (
                "Ваш друг подписался по вашей ссылке.\n"
                "Поздравляем, вы участвуете в розыгрыше!"
            )
        else:
            referrer_text = (
                "Ваш друг подписался по вашей ссылке.\n"
                "Чтобы участвовать в розыгрыше, подтвердите и свою подписку на канал."
            )
        try:
            await run_with_retry(
                bot.send_message,
                chat_id=confirmation_result.referrer_to_notify,
                text=referrer_text,
                logger=app_logger,
            )
        except (TelegramForbiddenError, TelegramBadRequest):
            app_logger.warning(
                "referrer_notification_failed",
                referrer_id=confirmation_result.referrer_to_notify,
            )
        except Exception:
            app_logger.exception(
                "referrer_notification_unexpected_error",
                referrer_id=confirmation_result.referrer_to_notify,
            )

    # If nothing changed, do not send duplicate messages; just show current progress.
    if not confirmation_result.user_subscription_changed and not confirmation_result.user_participant_changed:
        if confirmation_result.user_is_participant:
            await callback.answer("Вы уже участвуете в розыгрыше.")
            return

        referrals_needed = max(0, 1 - confirmation_result.referrals_confirmed)
        await callback.answer(
            f"Подписка уже подтверждена. Ждем подписку друга по вашей ссылке. Осталось друзей: {referrals_needed}.",
            show_alert=True,
        )
        return

    # Если подписка только что подтверждена - запрашиваем контакт
    if confirmation_result.user_subscription_changed and not confirmation_result.user_has_contact:
        await callback.answer("Подписка подтверждена.")
        if callback.message:
            try:
                await callback.message.delete()
            except Exception:
                pass
        app_logger.info(
            "requesting_simple_contact_after_subscription",
            tg_user_id=callback.from_user.id,
            has_contact=False,
        )
        await request_simple_contact(bot, callback.from_user.id, state, app_logger)
        return

    # Если подписка подтверждена и контакт есть, или пользователь стал участником
    response = "Спасибо, подписка подтверждена."
    referral_link = f"https://t.me/{bot_username}?start={callback.from_user.id}" if bot_username else ""

    if confirmation_result.user_is_participant:
        response += "\nПоздравляем! Вы участвуете в розыгрыше."
    else:
        response += (
            "\nТеперь отправьте другу вашу ссылку и попросите подписаться."
            "\nКак только друг подпишется, вы станете участником розыгрыша."
        )
        if referral_link:
            response += f"\n\nВаша ссылка:\n{referral_link}"

    if callback.message:
        try:
            await callback.message.edit_text(
                response,
                reply_markup=build_subscription_keyboard(channel_url),
            )
        except TelegramBadRequest:
            # Fallback for old/non-editable messages.
            await callback.message.answer(
                response,
                reply_markup=build_subscription_keyboard(channel_url),
            )

    await callback.answer("Статус обновлен.")
