"""Service layer for calendar alarms."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import db
from core.models import CalendarAlarm


class AlarmService:
    """CRUD helpers for :class:`CalendarAlarm`."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.session = session
        self._external = session is not None

    async def __aenter__(self) -> "AlarmService":
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

    async def create_alarm(
        self,
        *,
        owner_id: int,
        event_id: int,
        notify_at,
    ) -> CalendarAlarm:
        alarm = CalendarAlarm(
            owner_id=owner_id,
            event_id=event_id,
            notify_at=notify_at,
        )
        self.session.add(alarm)
        await self.session.flush()
        return alarm

    async def list_alarms(self, owner_id: Optional[int] = None) -> List[CalendarAlarm]:
        stmt = select(CalendarAlarm)
        if owner_id is not None:
            stmt = stmt.where(CalendarAlarm.owner_id == owner_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_alarm(self, alarm_id: int) -> bool:
        alarm = await self.session.get(CalendarAlarm, alarm_id)
        if alarm is None:
            return False
        await self.session.delete(alarm)
        await self.session.flush()
        return True
