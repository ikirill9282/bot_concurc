"""Referral repository helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import ReferralStatus
from app.db.models import Referral


class ReferralsRepository:
    @staticmethod
    async def create_pending_referral(
        session: AsyncSession,
        *,
        referrer_id: int,
        referral_id: int,
    ) -> bool:
        stmt = (
            insert(Referral)
            .values(
                referrer_id=referrer_id,
                referral_id=referral_id,
                status=ReferralStatus.PENDING,
                created_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_nothing(index_elements=[Referral.referral_id])
            .returning(Referral.id)
        )
        inserted_id = await session.scalar(stmt)
        return inserted_id is not None

    @staticmethod
    async def get_referral_by_referral_id(session: AsyncSession, referral_id: int) -> Referral | None:
        stmt = select(Referral).where(Referral.referral_id == referral_id)
        return await session.scalar(stmt)

    @staticmethod
    async def confirm_pending_referral(session: AsyncSession, referral_id: int) -> int | None:
        stmt = (
            update(Referral)
            .where(
                Referral.referral_id == referral_id,
                Referral.status == ReferralStatus.PENDING,
            )
            .values(
                status=ReferralStatus.CONFIRMED,
                confirmed_at=datetime.now(timezone.utc),
            )
            .returning(Referral.referrer_id)
        )
        return await session.scalar(stmt)

    @staticmethod
    async def count_confirmed_referrals(session: AsyncSession) -> int:
        stmt = select(func.count(Referral.id)).where(Referral.status == ReferralStatus.CONFIRMED)
        return int(await session.scalar(stmt) or 0)
