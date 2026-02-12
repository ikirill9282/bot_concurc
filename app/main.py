"""Webhook application entrypoint."""

from __future__ import annotations

import asyncio
from contextlib import suppress

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from sqlalchemy.ext.asyncio import AsyncEngine

from app.bot.router import build_router
from app.config import Settings, get_settings
from app.db.session import create_engine_and_session_factory
from app.logging_setup import configure_logging, get_logger
from app.web.health import healthz, readyz


def derive_channel_url(channel_id: int) -> str:
    channel = str(channel_id)
    normalized = channel[4:] if channel.startswith("-100") else channel.lstrip("-")
    return f"https://t.me/c/{normalized}"


async def resolve_channel_url(bot: Bot, settings: Settings, logger) -> str:
    if settings.channel_url:
        return settings.channel_url

    try:
        chat = await bot.get_chat(settings.channel_id)
        if getattr(chat, "username", None):
            return f"https://t.me/{chat.username}"
        if getattr(chat, "invite_link", None):
            return str(chat.invite_link)
    except TelegramAPIError:
        logger.warning("channel_url_auto_discovery_failed")
    except Exception:
        logger.warning("channel_url_auto_discovery_unexpected_error")

    return derive_channel_url(settings.channel_id)


def create_app(settings: Settings) -> web.Application:
    configure_logging(settings.log_level)
    logger = get_logger("giveaway_bot")

    engine, session_factory = create_engine_and_session_factory(settings.database_url)
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    dispatcher = Dispatcher()
    dispatcher.include_router(build_router())

    app = web.Application()
    app["session_factory"] = session_factory
    app["polling_task"] = None

    async def on_startup(application: web.Application) -> None:
        if settings.skip_webhook_setup:
            if settings.bot_username:
                bot_username = settings.bot_username
            else:
                me = await bot.get_me()
                bot_username = me.username or ""
            channel_url = settings.channel_url or derive_channel_url(settings.channel_id)
        else:
            me = await bot.get_me()
            bot_username = me.username or ""
            channel_url = await resolve_channel_url(bot, settings, logger)

        dispatcher.workflow_data.update(
            {
                "session_factory": session_factory,
                "settings": settings,
                "app_logger": logger,
                "bot_username": bot_username,
                "channel_url": channel_url,
            }
        )

        if settings.skip_webhook_setup:
            try:
                await bot.delete_webhook(drop_pending_updates=False)
            except TelegramAPIError:
                logger.warning("delete_webhook_failed_before_long_polling")

            polling_task = asyncio.create_task(
                dispatcher.start_polling(
                    bot,
                    allowed_updates=dispatcher.resolve_used_update_types(),
                )
            )
            application["polling_task"] = polling_task
            logger.warning("webhook_setup_skipped_for_local_mode")
            logger.info("long_polling_started")
            return

        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.resolved_webhook_secret,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        logger.info("webhook_configured", webhook_url=settings.webhook_url)

    async def on_shutdown(application: web.Application) -> None:
        if settings.skip_webhook_setup:
            polling_task = application.get("polling_task")
            if polling_task is not None and not polling_task.done():
                polling_task.cancel()
                with suppress(asyncio.CancelledError):
                    await polling_task
                logger.info("long_polling_stopped")
        else:
            try:
                await bot.delete_webhook(drop_pending_updates=False)
            except TelegramAPIError:
                logger.warning("webhook_delete_failed")

        await bot.session.close()

        async_engine: AsyncEngine = engine
        await async_engine.dispose()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_shutdown)

    app.router.add_get("/healthz", healthz)
    app.router.add_get("/readyz", readyz)

    webhook_handler = SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.resolved_webhook_secret,
    )
    webhook_handler.register(app, path="/webhook")
    setup_application(app, dispatcher, bot=bot)

    return app


def main() -> None:
    settings = get_settings()
    app = create_app(settings)
    web.run_app(app, host=settings.app_host, port=settings.app_port)


if __name__ == "__main__":
    main()
