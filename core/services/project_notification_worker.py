from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Iterable
from uuid import uuid4

from sqlalchemy import text

from core.db import async_session
from core.logger import logger
from core.utils import utcnow
from .project_notification_service import send_telegram_message

Sender = Callable[[int, str, bool], Awaitable[None]]


async def fetch_due_triggers(limit: int | None = None):
    now = utcnow()
    async with async_session() as session:
        res = await session.execute(
            text(
                "SELECT t.dedupe_key, t.rule, c.address "
                "FROM triggers t JOIN channels c ON t.channel_id = c.id "
                "WHERE t.next_fire_at <= :now ORDER BY t.next_fire_at"
            ).bindparams(now=now)
        )
        rows = res.mappings().all()
        if limit:
            rows = rows[:limit]
        return rows


async def mark_sent(dedupe_keys: Iterable[str]) -> None:
    async with async_session() as session:
        for key in dedupe_keys:
            await session.execute(
                text(
                    "INSERT INTO notifications (id, dedupe_key, sent_at) "
                    "VALUES (:id, :key, :sent_at) ON CONFLICT (dedupe_key) DO NOTHING"
                ),
                {"id": str(uuid4()), "key": key, "sent_at": utcnow()},
            )
        await session.commit()


async def run_worker(
    poll_interval: float = 60.0,
    sender: Sender | None = None,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Background loop sending project notifications."""
    _sender = sender or send_telegram_message
    _stop = stop_event or asyncio.Event()
    logger.info("Project notification worker: start")
    try:
        while not _stop.is_set():
            rows = await fetch_due_triggers()
            sent: list[str] = []
            for row in rows:
                addr = row["address"]
                rule = row["rule"] or {}
                text_msg = rule.get("text", "")
                silent = rule.get("silent", False)
                try:
                    await _sender(addr.get("chat_id"), text_msg, silent)
                    sent.append(row["dedupe_key"])
                except Exception:
                    logger.exception("Failed to send project notification")
            if sent:
                await mark_sent(sent)
                async with async_session() as session:
                    await session.execute(
                        text("DELETE FROM triggers WHERE dedupe_key = ANY(:keys)").bindparams(keys=sent)
                    )
                    await session.commit()
            try:
                await asyncio.wait_for(_stop.wait(), timeout=poll_interval)
            except asyncio.TimeoutError:
                pass
    finally:
        logger.info("Project notification worker: stop")
