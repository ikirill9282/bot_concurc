from app.db.models import User
from app.services.participation_service import mark_participant_if_eligible


def _build_user(*, subscribed: bool, confirmed_referrals: int, is_participant: bool = False) -> User:
    return User(
        tg_user_id=1,
        is_subscribed=subscribed,
        referrals_confirmed=confirmed_referrals,
        is_participant=is_participant,
    )


def test_user_does_not_become_participant_without_subscription() -> None:
    user = _build_user(subscribed=False, confirmed_referrals=5)
    assert mark_participant_if_eligible(user) is False
    assert user.is_participant is False


def test_user_does_not_become_participant_without_referrals() -> None:
    user = _build_user(subscribed=True, confirmed_referrals=0)
    assert mark_participant_if_eligible(user) is False
    assert user.is_participant is False


def test_user_becomes_participant_when_both_conditions_met() -> None:
    user = _build_user(subscribed=True, confirmed_referrals=1)
    assert mark_participant_if_eligible(user) is True
    assert user.is_participant is True
