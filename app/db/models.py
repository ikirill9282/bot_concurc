"""Database models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.db.enums import ReferralStatus


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_subscribed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    referred_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.tg_user_id", ondelete="SET NULL"),
        nullable=True,
    )
    referrals_confirmed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_participant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    last_subscription_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        CheckConstraint("referrer_id <> referral_id", name="ck_referrals_no_self_referral"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    referrer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.tg_user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    referral_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.tg_user_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[ReferralStatus] = mapped_column(
        Enum(
            ReferralStatus,
            name="referral_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=ReferralStatus.PENDING,
        server_default=ReferralStatus.PENDING.value,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
