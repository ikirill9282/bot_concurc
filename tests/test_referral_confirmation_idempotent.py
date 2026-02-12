from app.db.models import User
from app.services.participation_service import mark_participant_if_eligible


def _build_user(*, subscribed: bool, confirmed_referrals: int, is_participant: bool = False) -> User:
    return User(
        tg_user_id=1,
        is_subscribed=subscribed,
        referrals_confirmed=confirmed_referrals,
        is_participant=is_participant,
    )


def test_participation_marking_is_idempotent_after_first_transition() -> None:
    user = _build_user(subscribed=True, confirmed_referrals=1)

    first_transition = mark_participant_if_eligible(user)
    second_transition = mark_participant_if_eligible(user)

    assert first_transition is True
    assert second_transition is False
    assert user.is_participant is True
