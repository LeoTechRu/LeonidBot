import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from base import Base
from core.models import TaskStatus
from core.services.task_service import TaskService


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
async def test_task_creation_and_listing(session):
    service = TaskService(session)
    task = await service.create_task(owner_id=1, title="Test task")
    assert task.id is not None
    assert task.status == TaskStatus.pending
    tasks = await service.list_tasks(owner_id=1)
    assert len(tasks) == 1
    assert tasks[0].title == "Test task"
    assert tasks[0].status == TaskStatus.pending


@pytest.mark.asyncio
async def test_update_status(session):
    service = TaskService(session)
    task = await service.create_task(owner_id=1, title="Another")
    await service.update_status(task.id, TaskStatus.done)
    tasks = await service.list_tasks(owner_id=1)
    assert tasks[0].status == TaskStatus.done
