import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from base import Base
from core.services.reminder_service import ReminderService
from core.services.task_service import TaskService
from core.utils import utcnow


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    async with async_session() as sess:
        yield sess


@pytest.mark.asyncio
async def test_create_and_list_reminders(session):
    service = ReminderService(session)
    remind_at = utcnow()
    reminder = await service.create_reminder(
        owner_id=1, message="Ping", remind_at=remind_at
    )
    assert reminder.id is not None
    reminders = await service.list_reminders(owner_id=1)
    assert len(reminders) == 1
    assert reminders[0].message == "Ping"


@pytest.mark.asyncio
async def test_mark_done(session):
    service = ReminderService(session)
    remind_at = utcnow()
    reminder = await service.create_reminder(
        owner_id=1, message="Task", remind_at=remind_at
    )
    assert reminder.is_done is False
    updated = await service.mark_done(reminder.id)
    assert updated.is_done is True


@pytest.mark.asyncio
async def test_reminder_for_task(session):
    task_service = TaskService(session)
    task = await task_service.create_task(owner_id=1, title="Task with reminder")
    reminder_service = ReminderService(session)
    remind_at = utcnow()
    reminder = await reminder_service.create_reminder(
        owner_id=1, message="Task reminder", remind_at=remind_at, task_id=task.id
    )
    assert reminder.task_id == task.id
    reminders = await reminder_service.list_reminders(task_id=task.id)
    assert len(reminders) == 1
    assert reminders[0].message == "Task reminder"
