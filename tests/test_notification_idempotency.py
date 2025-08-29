import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import core.db as db
from base import Base
from core.services.reminder_service import ReminderService
from core.services.notification_service import run_reminder_dispatcher
from core.utils import utcnow


@pytest_asyncio.fixture
async def session_maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db.async_session = async_session
    try:
        yield async_session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_dispatch_idempotent(session_maker):
    async with ReminderService() as svc:
        await svc.create_reminder(owner_id=1, message="Ping", remind_at=utcnow())

    sent = []

    async def sender(owner_id: int, text: str) -> None:
        sent.append((owner_id, text))

    stop = asyncio.Event()
    task = asyncio.create_task(run_reminder_dispatcher(poll_interval=0.1, sender=sender, stop_event=stop))
    await asyncio.sleep(0.2)
    stop.set()
    await task
    assert len(sent) == 1

    sent.clear()
    stop = asyncio.Event()
    task = asyncio.create_task(run_reminder_dispatcher(poll_interval=0.1, sender=sender, stop_event=stop))
    await asyncio.sleep(0.2)
    stop.set()
    await task
    assert sent == []
