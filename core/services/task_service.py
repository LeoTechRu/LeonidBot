"""Service layer for task management."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import db
from core.models import Task
from core.utils import utcnow


class TaskService:
    """CRUD helpers for :class:`Task` objects."""

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self._external = session is not None

    async def __aenter__(self) -> "TaskService":
        if self.session is None:
            self.session = db.async_session()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if not self._external:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
            await self.session.close()

    async def create_task(
        self,
        *,
        user_id: int,
        title: str,
        description: str | None = None,
        due_date: datetime | None = None,
    ) -> Task:
        task = Task(
            user_id=user_id,
            title=title,
            description=description,
            due_date=due_date,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def get_task(self, task_id: int) -> Optional[Task]:
        result = await self.session.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def list_tasks(self, user_id: int | None = None) -> List[Task]:
        stmt = select(Task)
        if user_id is not None:
            stmt = stmt.where(Task.user_id == user_id)
        result = await self.session.execute(stmt.order_by(Task.created_at))
        return result.scalars().all()

    async def mark_completed(self, task_id: int, completed: bool = True) -> Optional[Task]:
        task = await self.get_task(task_id)
        if not task:
            return None
        task.completed = completed
        task.updated_at = utcnow()
        await self.session.flush()
        return task
