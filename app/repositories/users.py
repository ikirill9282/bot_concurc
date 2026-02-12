"""User repository helpers."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


class UsersRepository:
    @staticmethod
    async def get_by_tg_user_id(
        session: AsyncSession,
        tg_user_id: int,
        *,
        for_update: bool = False,
    ) -> User | None:
        stmt = select(User).where(User.tg_user_id == tg_user_id)
        if for_update:
            stmt = stmt.with_for_update()
        return await session.scalar(stmt)

    @staticmethod
    async def get_or_create_for_update(
        session: AsyncSession,
        tg_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> tuple[User, bool]:
        insert_stmt = (
            insert(User)
            .values(
                tg_user_id=tg_user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            .on_conflict_do_nothing(index_elements=[User.tg_user_id])
            .returning(User.id)
        )
        inserted_id = await session.scalar(insert_stmt)
        created = inserted_id is not None

        user = await UsersRepository.get_by_tg_user_id(session, tg_user_id, for_update=True)
        if user is None:
            raise RuntimeError(f"Unable to load user {tg_user_id} after upsert")

        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        return user, created

    @staticmethod
    async def exists_by_tg_user_id(session: AsyncSession, tg_user_id: int) -> bool:
        stmt = select(User.id).where(User.tg_user_id == tg_user_id).limit(1)
        return (await session.scalar(stmt)) is not None

    @staticmethod
    async def fetch_basic_stats(session: AsyncSession) -> dict[str, int]:
        total_users = int(await session.scalar(select(func.count(User.id))) or 0)
        total_subscribed = int(
            await session.scalar(select(func.count(User.id)).where(User.is_subscribed.is_(True))) or 0
        )
        total_participants = int(
            await session.scalar(select(func.count(User.id)).where(User.is_participant.is_(True))) or 0
        )

        return {
            "total_users": total_users,
            "total_subscribed": total_subscribed,
            "total_participants": total_participants,
        }

    @staticmethod
    async def fetch_export_rows(session: AsyncSession) -> list[tuple[int, str | None, int, bool, object]]:
        stmt = select(
            User.tg_user_id,
            User.username,
            User.referrals_confirmed,
            User.is_participant,
            User.created_at,
        ).order_by(User.id.asc())
        rows = await session.execute(stmt)
        return list(rows.all())

    @staticmethod
    async def fetch_all_tg_user_ids(session: AsyncSession) -> list[int]:
        stmt = select(User.tg_user_id).order_by(User.id.asc())
        rows = await session.scalars(stmt)
        return list(rows)
