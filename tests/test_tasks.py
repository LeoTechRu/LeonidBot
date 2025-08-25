import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from base import Base
from core.models import TgUser
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
    user = TgUser(telegram_id=1)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    svc = TaskService(session)
    task = await svc.create_task(owner_id=user.id, title="Test")
    assert task.id is not None
    tasks = await svc.list_tasks(user.id)
    assert len(tasks) == 1
    assert not tasks[0].is_completed
    await svc.complete_task(task.id)
    tasks = await svc.list_tasks(user.id)
    assert tasks[0].is_completed
