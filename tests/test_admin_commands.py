from app.bot.handlers.admin import is_admin_user
from app.services.admin_service import AdminStats, format_stats_message


def test_is_admin_user() -> None:
    admins = (100, 200, 300)
    assert is_admin_user(100, admins) is True
    assert is_admin_user(999, admins) is False
    assert is_admin_user(None, admins) is False


def test_format_stats_message() -> None:
    stats = AdminStats(
        total_users=10,
        total_subscribed=7,
        total_participants=3,
        total_confirmed_referrals=5,
    )
    text = format_stats_message(stats)

    assert "Total users: 10" in text
    assert "Subscribed users: 7" in text
    assert "Participants: 3" in text
    assert "Confirmed referrals: 5" in text
