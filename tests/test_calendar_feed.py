import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import core.db as db
from base import Base
from core.services.calendar_service import CalendarService
from core.services.task_service import TaskService
from core.services.calendar_token_service import CalendarTokenService
from core.models import TaskStatus
from web.routes.calendar import ui_router
from fastapi import FastAPI
from core.utils import utcnow


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db.async_session = async_session

    app = FastAPI()
    app.include_router(ui_router)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    await engine.dispose()


@pytest.mark.asyncio
async def test_feed_contains_events_and_tasks(client):
    # prepare token and data
    async with CalendarTokenService() as ts:
        token = await ts.create_token(owner_id=1)
    async with CalendarService() as cs:
        await cs.create_event(owner_id=1, title="E", start_at=utcnow())
    async with TaskService() as tsks:
        await tsks.create_task(owner_id=1, title="T", status=TaskStatus.todo)

    resp = await client.get("/calendar/feed.ics", params={"scope": "all", "token": token})
    assert resp.status_code == 200
    body = resp.text
    assert "VEVENT" in body and "VTODO" in body
    assert "VALARM" in body
