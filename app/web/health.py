"""Health and readiness handlers."""

from __future__ import annotations

from aiohttp import web
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def healthz(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def readyz(request: web.Request) -> web.Response:
    session_factory: async_sessionmaker[AsyncSession] = request.app["session_factory"]

    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return web.json_response({"status": "error"}, status=503)

    return web.json_response({"status": "ready"})
