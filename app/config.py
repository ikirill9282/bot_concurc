"""Environment-driven application configuration."""

from __future__ import annotations

import hashlib
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    channel_id: int = Field(alias="CHANNEL_ID")
    webhook_url: str | None = Field(default=None, alias="WEBHOOK_URL")
    admin_ids: tuple[int, ...] = Field(alias="ADMIN_IDS")

    webhook_secret: str | None = Field(default=None, alias="WEBHOOK_SECRET")
    skip_webhook_setup: bool = Field(default=False, alias="SKIP_WEBHOOK_SETUP")
    bot_username: str | None = Field(default=None, alias="BOT_USERNAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8080, alias="APP_PORT")
    channel_url: str | None = Field(default=None, alias="CHANNEL_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: object) -> tuple[int, ...]:
        """Parse ADMIN_IDS from comma-separated text into tuple[int]."""

        if isinstance(value, str):
            cleaned = [item.strip() for item in value.split(",") if item.strip()]
            if not cleaned:
                raise ValueError("ADMIN_IDS must contain at least one Telegram user ID")
            return tuple(int(item) for item in cleaned)

        if isinstance(value, int):
            return (value,)

        if isinstance(value, (list, tuple)):
            parsed = tuple(int(item) for item in value)
            if not parsed:
                raise ValueError("ADMIN_IDS must contain at least one Telegram user ID")
            return parsed

        raise ValueError("ADMIN_IDS must be a comma-separated string or a sequence")

    @field_validator("channel_id")
    @classmethod
    def validate_channel_id(cls, value: int) -> int:
        if not str(value).startswith("-100"):
            raise ValueError("CHANNEL_ID must be in format -100xxxxxxxxxx")
        return value

    @model_validator(mode="after")
    def validate_webhook_url(self) -> "Settings":
        """Validate that WEBHOOK_URL is provided when webhook mode is enabled."""
        if not self.skip_webhook_setup and not self.webhook_url:
            raise ValueError("WEBHOOK_URL is required when SKIP_WEBHOOK_SETUP=false")
        return self

    @property
    def resolved_webhook_secret(self) -> str:
        if self.webhook_secret:
            return self.webhook_secret
        return hashlib.sha256(self.bot_token.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
