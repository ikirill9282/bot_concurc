from app.services.referral_service import can_apply_referral, parse_ref_code


def test_parse_ref_code_handles_malformed_values() -> None:
    assert parse_ref_code(None) is None
    assert parse_ref_code("") is None
    assert parse_ref_code("abc") is None
    assert parse_ref_code("123") == 123


def test_can_apply_referral_rejects_self_referral() -> None:
    assert can_apply_referral(existing_referred_by=None, ref_code=10, user_id=10) is False


def test_can_apply_referral_rejects_overwrite() -> None:
    assert can_apply_referral(existing_referred_by=99, ref_code=11, user_id=10) is False


def test_can_apply_referral_accepts_valid_new_referral() -> None:
    assert can_apply_referral(existing_referred_by=None, ref_code=11, user_id=10) is True
