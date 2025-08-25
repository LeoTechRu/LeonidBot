import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from base import Base
from core.services.telegram_user_service import TelegramUserService
from core.services.task_service import TaskService


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as sess:
        yield sess


@pytest.mark.asyncio
async def test_create_and_complete_task(session):
    tsvc = TelegramUserService(session)
    user = await tsvc.update_from_telegram(telegram_id=1, username="tg")
    service = TaskService(session)
    task = await service.create_task(user_id=user.telegram_id, title="Test")
    assert task.id is not None

    tasks = await service.list_tasks(user.telegram_id)
    assert len(tasks) == 1 and tasks[0].title == "Test"

    await service.mark_completed(task.id)
    assert task.completed is True
