"""Application-wide constants."""

SUBSCRIPTION_RATE_LIMIT_SECONDS = 5
REFERRALS_REQUIRED_FOR_PARTICIPATION = 1
CHECK_SUBSCRIPTION_CALLBACK = "check_subscription"

VALID_SUBSCRIPTION_STATUSES = {
    "member",
    "administrator",
    "creator",
}

INVALID_SUBSCRIPTION_STATUSES = {
    "left",
    "kicked",
    "restricted",
}
