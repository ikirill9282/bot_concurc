"""Subscription checks and referral confirmation logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.stdlib import BoundLogger

from app.constants import SUBSCRIPTION_RATE_LIMIT_SECONDS
from app.repositories.referrals import ReferralsRepository
from app.repositories.users import UsersRepository
from app.services.participation_service import mark_participant_if_eligible


@dataclass(slots=True)
class SubscriptionConfirmationResult:
    referral_confirmed: bool
    referrer_to_notify: int | None
    referrer_is_participant: bool | None
    user_subscription_changed: bool
    user_participant_changed: bool
    referrals_confirmed: int
    user_is_participant: bool
    user_has_contact: bool


def normalize_member_status(raw_status: object) -> str:
    if hasattr(raw_status, "value"):
        return str(getattr(raw_status, "value"))
    return str(raw_status)


def compute_retry_after_seconds(
    last_checked_at: datetime | None,
    now: datetime,
    cooldown_seconds: int = SUBSCRIPTION_RATE_LIMIT_SECONDS,
) -> int:
    if last_checked_at is None:
        return 0

    elapsed = now - last_checked_at
    if elapsed >= timedelta(seconds=cooldown_seconds):
        return 0

    remaining = timedelta(seconds=cooldown_seconds) - elapsed
    return max(1, math.ceil(remaining.total_seconds()))


async def register_subscription_check_attempt(
    session_factory: async_sessionmaker[AsyncSession],
    telegram_user: TelegramUser,
    logger: BoundLogger,
) -> int:
    now = datetime.now(timezone.utc)

    async with session_factory() as session:
        async with session.begin():
            user, created = await UsersRepository.get_or_create_for_update(
                session,
                tg_user_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
            )

            if created:
                logger.info("user_created", tg_user_id=user.tg_user_id)

            retry_after = compute_retry_after_seconds(user.last_subscription_check_at, now)
            if retry_after > 0:
                return retry_after

            user.last_subscription_check_at = now

    return 0


async def confirm_subscription_and_referral(
    session_factory: async_sessionmaker[AsyncSession],
    tg_user_id: int,
    logger: BoundLogger,
) -> SubscriptionConfirmationResult:
    async with session_factory() as session:
        async with session.begin():
            user = await UsersRepository.get_by_tg_user_id(session, tg_user_id, for_update=True)
            if user is None:
                raise ValueError(f"User {tg_user_id} must exist before subscription confirmation")

            was_subscribed = user.is_subscribed
            was_participant = user.is_participant
            user.is_subscribed = True
            mark_participant_if_eligible(user)

            referrer_id = await ReferralsRepository.confirm_pending_referral(session, tg_user_id)

            referral_confirmed = referrer_id is not None
            notify_referrer_id: int | None = None
            referrer_is_participant: bool | None = None

            if referrer_id is not None:
                if referrer_id == tg_user_id:
                    logger.warning("self_referral_detected_during_confirmation", tg_user_id=tg_user_id)
                else:
                    referrer = await UsersRepository.get_by_tg_user_id(session, referrer_id, for_update=True)
                    if referrer is not None:
                        referrer.referrals_confirmed += 1
                        mark_participant_if_eligible(referrer)
                        notify_referrer_id = referrer_id
                        referrer_is_participant = referrer.is_participant
                        logger.info(
                            "referral_confirmed",
                            referrer_id=referrer_id,
                            referral_id=tg_user_id,
                        )

            mark_participant_if_eligible(user)

            return SubscriptionConfirmationResult(
                referral_confirmed=referral_confirmed,
                referrer_to_notify=notify_referrer_id,
                referrer_is_participant=referrer_is_participant,
                user_subscription_changed=(not was_subscribed and user.is_subscribed),
                user_participant_changed=(not was_participant and user.is_participant),
                referrals_confirmed=user.referrals_confirmed,
                user_is_participant=user.is_participant,
                user_has_contact=bool(user.contact_name and user.contact_phone),
            )
