"""Referral and /start command business logic."""

from __future__ import annotations

from dataclasses import dataclass

from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.stdlib import BoundLogger

from app.repositories.referrals import ReferralsRepository
from app.repositories.users import UsersRepository


@dataclass(slots=True)
class StartProcessingResult:
    tg_user_id: int
    created: bool
    referral_applied: bool


def parse_ref_code(raw_value: str | None) -> int | None:
    if not raw_value:
        return None

    try:
        return int(raw_value.strip())
    except (TypeError, ValueError):
        return None


def can_apply_referral(existing_referred_by: int | None, ref_code: int | None, user_id: int) -> bool:
    if ref_code is None:
        return False
    if existing_referred_by is not None:
        return False
    if ref_code == user_id:
        return False
    return True


async def process_start_command(
    session_factory: async_sessionmaker[AsyncSession],
    telegram_user: TelegramUser,
    start_argument: str | None,
    logger: BoundLogger,
) -> StartProcessingResult:
    parsed_ref_code = parse_ref_code(start_argument)

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

            referral_applied = False

            if can_apply_referral(user.referred_by, parsed_ref_code, user.tg_user_id):
                assert parsed_ref_code is not None
                referrer_exists = await UsersRepository.exists_by_tg_user_id(session, parsed_ref_code)
                if referrer_exists:
                    created_referral = await ReferralsRepository.create_pending_referral(
                        session,
                        referrer_id=parsed_ref_code,
                        referral_id=user.tg_user_id,
                    )
                    if created_referral:
                        user.referred_by = parsed_ref_code
                        referral_applied = True
                        logger.info(
                            "referral_created",
                            referrer_id=parsed_ref_code,
                            referral_id=user.tg_user_id,
                        )
                    else:
                        existing_referral = await ReferralsRepository.get_referral_by_referral_id(
                            session,
                            referral_id=user.tg_user_id,
                        )
                        if existing_referral is not None:
                            user.referred_by = existing_referral.referrer_id
                else:
                    logger.info(
                        "referral_skipped_referrer_not_found",
                        referral_id=user.tg_user_id,
                        provided_referrer_id=parsed_ref_code,
                    )

        return StartProcessingResult(
            tg_user_id=telegram_user.id,
            created=created,
            referral_applied=referral_applied,
        )
