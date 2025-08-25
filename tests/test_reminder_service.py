import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from base import Base
from core.services.task_service import TaskService
from core.services.reminder_service import ReminderService
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
async def test_create_and_list_task_reminder(session):
    task_service = TaskService(session)
    task = await task_service.create_task(owner_id=1, title="Test")
    service = ReminderService(session)
    reminder = await service.create_reminder(
        owner_id=1, task_id=task.id, remind_at=utcnow(), message="check"
    )
    assert reminder.id is not None
    reminders = await service.list_reminders(task_id=task.id)
    assert len(reminders) == 1
    assert reminders[0].task_id == task.id
