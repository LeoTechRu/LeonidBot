from __future__ import annotations

import json
import os
from typing import Any, Dict
from uuid import UUID, uuid4

import aiohttp
from sqlalchemy import text

from core.db import async_session
from core.logger import logger

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def send_telegram_message(chat_id: int, text: str, silent: bool = False) -> None:
    """Send message to Telegram chat via Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not configured")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_notification": silent}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                body = await resp.text()
                logger.error("Telegram API error %s: %s", resp.status, body)


async def add_project_notification(project_id: UUID, channel: Dict[str, Any], rules: Dict[str, Any]) -> UUID:
    """Register channel for project notifications."""
    channel_id = uuid4()
    async with async_session() as session:
        await session.execute(
            text("INSERT INTO channels (id, type, address) VALUES (:id, :type, :address)"),
            {"id": channel_id, "type": channel["type"], "address": json.dumps(channel["address"])}
        )
        await session.execute(
            text(
                "INSERT INTO project_notifications (project_id, channel_id, rules) "
                "VALUES (:pid, :cid, :rules) "
                "ON CONFLICT (project_id, channel_id) DO UPDATE SET rules = :rules"
            ),
            {"pid": project_id, "cid": channel_id, "rules": json.dumps(rules)}
        )
        await session.commit()
    return channel_id
