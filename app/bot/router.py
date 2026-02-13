"""Router assembly."""

from aiogram import Router

from app.bot.handlers import admin, contact, errors, start, subscription


def build_router() -> Router:
    router = Router(name="root")
    router.include_router(start.router)
    router.include_router(subscription.router)
    router.include_router(contact.router)
    router.include_router(admin.router)
    router.include_router(errors.router)
    return router
