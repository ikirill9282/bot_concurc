"""Admin command services."""

from __future__ import annotations

import asyncio
import csv
from dataclasses import dataclass
from io import StringIO

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.stdlib import BoundLogger

from app.repositories.referrals import ReferralsRepository
from app.repositories.users import UsersRepository
from app.services.telegram_retry import run_with_retry


@dataclass(slots=True)
class AdminStats:
    total_users: int
    total_subscribed: int
    total_participants: int
    total_confirmed_referrals: int


@dataclass(slots=True)
class BroadcastResult:
    delivered: int
    failed: int


async def collect_admin_stats(session_factory: async_sessionmaker[AsyncSession]) -> AdminStats:
    async with session_factory() as session:
        basic_stats = await UsersRepository.fetch_basic_stats(session)
        total_confirmed_referrals = await ReferralsRepository.count_confirmed_referrals(session)

    return AdminStats(
        total_users=basic_stats["total_users"],
        total_subscribed=basic_stats["total_subscribed"],
        total_participants=basic_stats["total_participants"],
        total_confirmed_referrals=total_confirmed_referrals,
    )


def format_stats_message(stats: AdminStats) -> str:
    return (
        "Giveaway Stats\n"
        f"Total users: {stats.total_users}\n"
        f"Subscribed users: {stats.total_subscribed}\n"
        f"Participants: {stats.total_participants}\n"
        f"Confirmed referrals: {stats.total_confirmed_referrals}"
    )


async def export_users_csv(session_factory: async_sessionmaker[AsyncSession]) -> bytes:
    async with session_factory() as session:
        rows = await UsersRepository.fetch_export_rows(session)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "tg_user_id",
            "username",
            "referrals_confirmed",
            "is_participant",
            "created_at",
        ]
    )

    for row in rows:
        writer.writerow(
            [
                row[0],
                row[1] or "",
                row[2],
                row[3],
                row[4].isoformat() if row[4] else "",
            ]
        )

    return buffer.getvalue().encode("utf-8")


async def broadcast_to_all_users(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    message_text: str,
    logger: BoundLogger,
) -> BroadcastResult:
    async with session_factory() as session:
        tg_user_ids = await UsersRepository.fetch_all_tg_user_ids(session)

    delivered = 0
    failed = 0

    for tg_user_id in tg_user_ids:
        try:
            await run_with_retry(
                bot.send_message,
                chat_id=tg_user_id,
                text=message_text,
                logger=logger,
            )
            delivered += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
            logger.warning("broadcast_delivery_failed", tg_user_id=tg_user_id)
        except Exception:
            failed += 1
            logger.exception("broadcast_unexpected_error", tg_user_id=tg_user_id)

        await asyncio.sleep(0.05)

    return BroadcastResult(delivered=delivered, failed=failed)
