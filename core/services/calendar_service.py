"""Service layer for calendar event operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import db
from core.models import CalendarEvent


class CalendarService:
    """CRUD helpers for the :class:`CalendarEvent` model."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.session = session
        self._external = session is not None

    async def __aenter__(self) -> "CalendarService":
        if self.session is None:
            self.session = db.async_session()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover
        if not self._external:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
            await self.session.close()

    async def create_event(
        self,
        owner_id: int,
        title: str,
        start_at,
        end_at=None,
        description: str | None = None,
        project_id: int | None = None,
        area_id: int | None = None,
    ) -> CalendarEvent:
        """Create a new calendar event for the given owner."""

        event = CalendarEvent(
            owner_id=owner_id,
            title=title,
            start_at=start_at,
            end_at=end_at,
            description=description,
            project_id=project_id,
            area_id=area_id,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_events(self, owner_id: Optional[int] = None) -> List[CalendarEvent]:
        """Return events, optionally filtered by owner."""

        stmt = select(CalendarEvent)
        if owner_id is not None:
            stmt = stmt.where(CalendarEvent.owner_id == owner_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_agenda(
        self,
        owner_id: int,
        start,
        end,
        project_id: int | None = None,
    ) -> List[CalendarEvent]:
        """Return events for owner in the given time range."""

        stmt = select(CalendarEvent).where(
            CalendarEvent.owner_id == owner_id,
            CalendarEvent.start_at >= start,
            CalendarEvent.start_at <= end,
        )
        if project_id is not None:
            stmt = stmt.where(CalendarEvent.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

