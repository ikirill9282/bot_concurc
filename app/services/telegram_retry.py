"""Retry helpers for Telegram API calls."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, TypeVar

from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramServerError
from structlog.stdlib import BoundLogger

T = TypeVar("T")


async def run_with_retry(
    operation: Callable[..., Awaitable[T]],
    *args: Any,
    attempts: int = 3,
    base_delay_seconds: float = 1.0,
    logger: BoundLogger | None = None,
    **kwargs: Any,
) -> T:
    """Run Telegram operation with retry for transient failures."""

    for attempt in range(1, attempts + 1):
        try:
            return await operation(*args, **kwargs)
        except TelegramRetryAfter as exc:
            if attempt >= attempts:
                raise
            delay = float(exc.retry_after or base_delay_seconds)
            if logger is not None:
                logger.warning(
                    "telegram_retry_after",
                    attempt=attempt,
                    attempts=attempts,
                    delay_seconds=delay,
                )
            await asyncio.sleep(delay)
        except (TelegramNetworkError, TelegramServerError):
            if attempt >= attempts:
                raise
            delay = base_delay_seconds * (2 ** (attempt - 1))
            if logger is not None:
                logger.warning(
                    "telegram_transient_error_retry",
                    attempt=attempt,
                    attempts=attempts,
                    delay_seconds=delay,
                )
            await asyncio.sleep(delay)

    raise RuntimeError("unreachable retry state")
