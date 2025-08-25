from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Task


class TaskService:
    """CRUD operations for :class:`Task` objects."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_task(
        self,
        owner_id: int,
        title: str,
        description: str | None = None,
        due_date: datetime | None = None,
    ) -> Task:
        task = Task(
            owner_id=owner_id,
            title=title,
            description=description,
            due_date=due_date,
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def list_tasks(self, owner_id: int) -> list[Task]:
        result = await self.session.execute(
            select(Task).where(Task.owner_id == owner_id)
        )
        return result.scalars().all()

    async def complete_task(self, task_id: int) -> None:
        task = await self.session.get(Task, task_id)
        if task is None:
            raise ValueError("Task not found")
        task.is_completed = True
        await self.session.commit()
