from datetime import datetime, timedelta, timezone

from app.services.subscription_service import compute_retry_after_seconds


def test_rate_limit_allows_when_no_previous_check() -> None:
    now = datetime.now(timezone.utc)
    assert compute_retry_after_seconds(None, now, cooldown_seconds=5) == 0


def test_rate_limit_blocks_with_remaining_seconds() -> None:
    now = datetime.now(timezone.utc)
    last_check = now - timedelta(seconds=2)
    assert compute_retry_after_seconds(last_check, now, cooldown_seconds=5) == 3


def test_rate_limit_allows_after_cooldown() -> None:
    now = datetime.now(timezone.utc)
    last_check = now - timedelta(seconds=7)
    assert compute_retry_after_seconds(last_check, now, cooldown_seconds=5) == 0
