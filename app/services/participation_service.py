"""Participation business rules."""

from __future__ import annotations

from app.constants import REFERRALS_REQUIRED_FOR_PARTICIPATION
from app.db.models import User


def mark_participant_if_eligible(user: User) -> bool:
    """Mark user as participant once both conditions are met.

    The transition is one-way and idempotent.
    """

    if user.is_participant:
        return False

    if user.is_subscribed and user.referrals_confirmed >= REFERRALS_REQUIRED_FOR_PARTICIPATION:
        user.is_participant = True
        return True

    return False
