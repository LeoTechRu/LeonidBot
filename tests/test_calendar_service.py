import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from base import Base
from core.services.calendar_service import CalendarService
from datetime import datetime


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as sess:
        yield sess


@pytest.mark.asyncio
async def test_calendar_event_create_and_list(session):
    service = CalendarService(session)
    event = await service.create_event(owner_id=1, title="Meeting", start_at=datetime(2024, 1, 1))
    assert event.id is not None
    events = await service.list_events(owner_id=1)
    assert len(events) == 1
    assert events[0].title == "Meeting"


@pytest.mark.asyncio
async def test_list_agenda_filters_range(session):
    service = CalendarService(session)
    await service.create_event(owner_id=1, title="Day1", start_at=datetime(2024, 1, 1))
    await service.create_event(owner_id=1, title="Day2", start_at=datetime(2024, 1, 2))
    events = await service.list_agenda(1, datetime(2024, 1, 1), datetime(2024, 1, 1, 23, 59, 59))
    assert len(events) == 1
    assert events[0].title == "Day1"
