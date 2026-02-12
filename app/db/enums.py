"""Database enums."""

from enum import Enum


class ReferralStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
