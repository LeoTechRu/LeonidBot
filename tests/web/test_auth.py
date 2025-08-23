import hmac
import hashlib
import time

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from base import Base
import db
from web.config import S

try:
    from core.main import app  # type: ignore
except ModuleNotFoundError:  # fallback if app located differently
    from main import app  # type: ignore


BOT_TOKEN = "TEST_TOKEN"


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
    db.async_session = async_session
    S.BOT_TOKEN = BOT_TOKEN
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    await engine.dispose()


@pytest.mark.asyncio
async def test_telegram_login_validation(client: AsyncClient):
    data = {
        "id": 123,
        "first_name": "Test",
        "auth_date": int(time.time()),
    }
    data["hash"] = _generate_hash(data)
    response = await client.post("/auth/callback", data=data)
    assert response.status_code in {302, 303}
    assert response.headers.get("location", "").endswith("/admin")
    assert response.cookies.get("telegram_id") == "123"

    data["hash"] = "invalid"
    bad = await client.post("/auth/callback", data=data)
    assert bad.status_code in {400, 401, 403}
