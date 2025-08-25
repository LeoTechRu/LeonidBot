"""Generic CRUD services for extended models."""
from __future__ import annotations

from typing import Generic, TypeVar, Type, Optional, List
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import db
from core.models import (
    Area,
    Project,
    Habit,
    Resource,
    Archive,
    OKR,
    KeyResult,
    Interface,
    Limit,
    Role,
    Perm,
    UserRoleLink,
    Link,
)

T = TypeVar("T", bound=db.Base)


class CRUDService(Generic[T]):
    """Minimal async CRUD helper."""

    def __init__(
        self,
        model: Type[T],
        session: Optional[AsyncSession] = None,
    ) -> None:
        self.model = model
        self.session = session
        self._external = session is not None

    async def __aenter__(self) -> "CRUDService[T]":
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

    async def create(self, **kwargs) -> T:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get(self, obj_id: int) -> T | None:
        return await self.session.get(self.model, obj_id)

    async def list(self, **filters) -> List[T]:
        stmt = select(self.model)
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update(self, obj_id: int, **kwargs) -> T | None:
        obj = await self.get(obj_id)
        if obj is None:
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self.session.flush()
        return obj

    async def delete(self, obj_id: int) -> bool:
        obj = await self.get(obj_id)
        if obj is None:
            return False
        await self.session.delete(obj)
        return True


class AreaService(CRUDService[Area]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(Area, session)


class ProjectService(CRUDService[Project]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(Project, session)


class HabitService(CRUDService[Habit]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(Habit, session)

    async def toggle_progress(
        self, habit_id: int, day: date | None = None
    ) -> bool:
        """Toggle completion state for a habit on a specific day.

        Progress is stored inside the ``metrics`` JSON field under the key
        ``"progress"`` as a mapping ``{date_str: bool}`` where ``date_str`` is
        an ISO formatted string. When toggled to ``True`` the day is marked as
        completed, otherwise it is removed/marked as not completed.

        Args:
            habit_id: ID of the habit to update.
            day: Date for which the progress should be toggled. Defaults to
                today.

        Returns:
            ``True`` if the habit was found and updated, ``False`` otherwise.
        """
        habit = await self.get(habit_id)
        if habit is None:
            return False

        metrics = habit.metrics or {}
        progress: dict = metrics.get("progress", {}) or {}
        day_str = (day or date.today()).isoformat()
        current = progress.get(day_str, False)
        progress[day_str] = not current
        metrics["progress"] = progress
        habit.metrics = metrics
        await self.session.flush()
        return True


class ResourceService(CRUDService[Resource]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(Resource, session)


class ArchiveService(CRUDService[Archive]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(Archive, session)


class OKRService(CRUDService[OKR]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(OKR, session)


class KeyResultService(CRUDService[KeyResult]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(KeyResult, session)


class InterfaceService(CRUDService[Interface]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(Interface, session)


class LimitService(CRUDService[Limit]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(Limit, session)


class RoleService(CRUDService[Role]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(Role, session)


class PermService(CRUDService[Perm]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(Perm, session)


class UserRoleService(CRUDService[UserRoleLink]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(UserRoleLink, session)


class LinkService(CRUDService[Link]):
    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        super().__init__(Link, session)

    async def related(self, source_id: int, link_type: str | None = None):
        stmt = select(Link).where(Link.source_id == source_id)
        if link_type is not None:
            stmt = stmt.where(Link.link_type == link_type)
        result = await self.session.execute(stmt)
        return result.scalars().all()
