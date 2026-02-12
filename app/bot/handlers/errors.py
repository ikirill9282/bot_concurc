"""Global error handler to avoid update-processing crashes."""

from __future__ import annotations

from aiogram import Router
from aiogram.types.error_event import ErrorEvent
from structlog.stdlib import BoundLogger

router = Router(name=__name__)


@router.error()
async def handle_errors(event: ErrorEvent, app_logger: BoundLogger) -> bool:
    app_logger.exception("unhandled_update_exception", error=str(event.exception))
    return True
