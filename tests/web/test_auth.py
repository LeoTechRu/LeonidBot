import hmac
import hashlib

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from base import Base
import core.db as db
import core.services.telegram as telegram_service

from web.main import app  # приложение располагается в пакете web
import web.main as main


BOT_TOKEN = "TEST_TOKEN"

# Используем тестовый токен как в приложении, так и в модуле базы данных
main.BOT_TOKEN = BOT_TOKEN
db.BOT_TOKEN = BOT_TOKEN


def _generate_hash(data: dict) -> str:
    """Generate Telegram auth hash."""
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()) if k != "hash")
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    return hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Подменяем сессии, чтобы использовать тестовую БД SQLite
    db.async_session = async_session
    telegram_service.async_session = async_session
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    await engine.dispose()


@pytest.mark.asyncio
async def test_telegram_login_validation(client: AsyncClient):
    data = {
        "id": 123,
        "first_name": "Test",
        "auth_date": 111111,
    }
    data["hash"] = _generate_hash(data)
    response = await client.get("/auth/telegram", params=data)
    assert response.status_code == 200

    data["hash"] = "invalid"
    bad = await client.get("/auth/telegram", params=data)
    assert bad.status_code in {400, 401, 403}

