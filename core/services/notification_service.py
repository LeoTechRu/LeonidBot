"""Фоновая рассылка напоминаний.

Реализует простой цикл опроса базы напоминаний и отправку уведомлений.
По умолчанию модуль не выполняет сетевых вызовов и может использоваться
как заглушка (например, в тестовой среде). Для продакшена можно передать
функцию-отправитель, которая шлёт сообщения в Telegram.
"""

from __future__ import annotations

import asyncio
import os
from typing import Awaitable, Callable, Iterable

from core.logger import logger
from core.utils import utcnow
from .reminder_service import ReminderService
from .alarm_service import AlarmService
from core.models import CalendarEvent
from core.db import bot


Sender = Callable[[int, str], Awaitable[None]]


async def default_sender(owner_id: int, text: str) -> None:
    """Отправитель по умолчанию: просто логируем сообщение.

    Безопасно для офлайн/тестовой среды.
    """
    logger.info(f"[reminder] →{owner_id}: {text}")


async def telegram_sender(chat_id: int, text: str) -> None:
    """Send a Telegram message using the global bot."""
    try:
        await bot.send_message(chat_id, text)
    except Exception:
        logger.exception("Не удалось отправить сообщение", extra={"chat_id": chat_id})


async def fetch_due_reminders(limit: int | None = None):
    """Вернуть просроченные и текущие напоминания (is_done = False)."""
    now = utcnow()
    async with ReminderService() as service:
        # Ленивая выборка: отфильтруем на стороне Python для универсальности
        reminders = await service.list_reminders()
        due = [r for r in reminders if not r.is_done and r.remind_at <= now]
        if limit:
            due = due[:limit]
        return due


async def mark_done(ids: Iterable[int]) -> None:
    async with ReminderService() as service:
        for rid in ids:
            try:
                await service.mark_done(rid)
            except Exception:
                logger.exception("Не удалось отметить напоминание выполненным", extra={"id": rid})


async def run_reminder_dispatcher(
    *,
    poll_interval: float = 60.0,
    sender: Sender | None = None,
    jitter: float = 5.0,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Простой цикл рассылки напоминаний.

    - ``poll_interval``: базовый интервал опроса (сек)
    - ``sender``: корутина-отправитель уведомления (owner_id, text) → None
    - ``jitter``: небольшой случайный дрожащий сдвиг, чтобы избежать срезонанса
    - ``stop_event``: внешний сигнал остановки; если не задан — создаётся внутренний
    """
    import random

    _sender = sender or default_sender
    _stop = stop_event or asyncio.Event()
    logger.info("Reminder dispatcher: старт")
    try:
        while not _stop.is_set():
            due = await fetch_due_reminders()
            if due:
                logger.debug(f"Reminder dispatcher: к отправке {len(due)} шт.")
            sent_ids: list[int] = []
            for r in due:
                try:
                    await _sender(r.owner_id, r.message)
                    sent_ids.append(r.id)
                except Exception:
                    logger.exception("Ошибка отправки напоминания", extra={"id": r.id})
            if sent_ids:
                await mark_done(sent_ids)
            # сон с джиттером
            sleep_for = poll_interval + random.uniform(0, max(jitter, 0.0))
            try:
                await asyncio.wait_for(_stop.wait(), timeout=sleep_for)
            except asyncio.TimeoutError:
                pass
    finally:
        logger.info("Reminder dispatcher: остановка")


async def fetch_due_alarms(limit: int | None = None):
    """Вернуть просроченные тревоги календаря."""
    now = utcnow()
    async with AlarmService() as service:
        alarms = await service.list_alarms()
        due = [a for a in alarms if a.notify_at <= now]
        if limit:
            due = due[:limit]
        return due


async def run_alarm_dispatcher(
    *,
    poll_interval: float = 60.0,
    sender: Sender | None = None,
    jitter: float = 5.0,
    stop_event: asyncio.Event | None = None,
) -> None:
    """Цикл отправки тревог календаря."""
    import random

    _sender = sender or telegram_sender
    _stop = stop_event or asyncio.Event()
    logger.info("Alarm dispatcher: старт")
    try:
        while not _stop.is_set():
            due = await fetch_due_alarms()
            if due:
                logger.debug(f"Alarm dispatcher: к отправке {len(due)} шт.")
            for a in due:
                try:
                    async with AlarmService() as svc:
                        event = await svc.session.get(CalendarEvent, a.event_id)
                        text = event.title if event else "Событие"
                        await _sender(a.owner_id, text)
                        from web.config import S
                        channel_id = getattr(S, "NOTIFY_CHANNEL_ID", None)
                        if channel_id:
                            await _sender(int(channel_id), text)
                        await svc.delete_alarm(a.id)
                except Exception:
                    logger.exception("Ошибка отправки тревоги", extra={"id": a.id})
            sleep_for = poll_interval + random.uniform(0, max(jitter, 0.0))
            try:
                await asyncio.wait_for(_stop.wait(), timeout=sleep_for)
            except asyncio.TimeoutError:
                pass
    finally:
        logger.info("Alarm dispatcher: остановка")


def is_scheduler_enabled() -> bool:
    """Флаг включения из окружения.

    ENABLE_SCHEDULER=1 — включает планировщик.
    """
    return str(os.getenv("ENABLE_SCHEDULER", "0")).lower() in {"1", "true", "yes"}

