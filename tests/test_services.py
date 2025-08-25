import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from base import Base
from core.services.telegram_user_service import TelegramUserService
from core.services.web_user_service import WebUserService
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
async def test_registration_and_auth(session):
    service = WebUserService(session)
    user = await service.register(username="alice", password="secret")
    assert user.id is not None
    auth = await service.authenticate("alice", "secret")
    assert auth is not None
    assert await service.authenticate("alice", "bad") is None


@pytest.mark.asyncio
async def test_binding_flow(session):
    tsvc = TelegramUserService(session)
    tg_user = await tsvc.update_from_telegram(telegram_id=123, username="tg")
    wsvc = WebUserService(session)
    web_user = await wsvc.register(username="alice", password="secret")
    await wsvc.link_telegram(web_user.id, tg_user.id)
    with pytest.raises(ValueError):
        await wsvc.link_telegram(web_user.id, tg_user.id)
    other = await wsvc.register(username="bob", password="x")
    with pytest.raises(ValueError):
        await wsvc.link_telegram(other.id, tg_user.id)
    await wsvc.unlink_telegram(web_user.id)
    assert web_user.telegram_user_id is None


@pytest.mark.asyncio
async def test_update_profile_and_lookup(session):
    wsvc = WebUserService(session)
    tsvc = TelegramUserService(session)
    tg_user = await tsvc.update_from_telegram(telegram_id=555, username="tg")
    user = await wsvc.register(username="alice", password="secret")
    await wsvc.link_telegram(user.id, tg_user.id)
    await wsvc.update_profile(user.id, {"birthday": "2001-01-02"})
    assert str(user.birthday) == "2001-01-02"
    await wsvc.update_profile(user.id, {"birthday": "02.01.2001"})
    assert str(user.birthday) == "2001-01-02"
    by_id = await wsvc.get_user_by_identifier("alice")
    assert by_id.id == user.id
    by_tg = await wsvc.get_user_by_identifier(555)
    assert by_tg.id == user.id


@pytest.mark.asyncio
async def test_task_service_flow(session):
    tsvc = TelegramUserService(session)
    await tsvc.create_user(telegram_id=1, username="alice")
    svc = TaskService(session)
    task = await svc.create_task(owner_id=1, title="Test task")
    assert task.id is not None
    tasks = await svc.list_tasks(owner_id=1)
    assert len(tasks) == 1
    assert tasks[0].title == "Test task"
    await svc.mark_done(task.id)
    tasks = await svc.list_tasks(owner_id=1)
    assert tasks[0].is_done is True
