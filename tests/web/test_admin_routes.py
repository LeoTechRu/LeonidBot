import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from base import Base
from core.models import User, UserRole
import core.db as db
import core.services.telegram as telegram_service

# Приложение FastAPI после рефакторинга находится в пакете web
from web.main import app  # type: ignore


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Подменяем сессии в модуле базы и сервисах, чтобы использовать SQLite
    db.async_session = async_session
    telegram_service.async_session = async_session
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    await engine.dispose()


async def _create_user(role: UserRole, telegram_id: int) -> None:
    async with db.async_session() as session:  # type: ignore
        async with session.begin():
            session.add(User(telegram_id=telegram_id, first_name="T", role=role.value))


@pytest.mark.asyncio
async def test_profile_access_single_user(client: AsyncClient):
    await _create_user(UserRole.single, telegram_id=1)
    resp = await client.get("/profile", headers={"X-Telegram-Id": "1"})
    assert resp.status_code == 200

    admin = await client.get("/admin/dashboard", headers={"X-Telegram-Id": "1"})
    assert admin.status_code in {401, 403}


@pytest.mark.asyncio
async def test_admin_access(client: AsyncClient):
    await _create_user(UserRole.admin, telegram_id=2)
    profile = await client.get("/profile", headers={"X-Telegram-Id": "2"})
    assert profile.status_code == 200
    admin = await client.get("/admin/dashboard", headers={"X-Telegram-Id": "2"})
    assert admin.status_code == 200

