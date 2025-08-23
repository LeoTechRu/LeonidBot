from db import async_session
from logger import logger
from models import Group, UserGroup, GroupType, User
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Tuple


class GroupService:
    def __init__(self, session: AsyncSession | None = None):
        self.session = session
        self._external = session is not None

    async def __aenter__(self):
        if not self._external:
            self.session = async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self.session.commit()
        else:
            await self.session.rollback()
        if not self._external:
            await self.session.close()

    async def get_or_create_group(self, telegram_id: int, **kwargs) -> Tuple[Group, bool]:
        group = await self.get_group_by_telegram_id(telegram_id)
        if group:
            return group, False
        required_fields = {
            "telegram_id": telegram_id,
            "title": kwargs.get("title", f"Group_{telegram_id}"),
            "type": kwargs.get("type", GroupType.private),
            "owner_id": kwargs.get("owner_id", telegram_id),
        }
        group = await self.create_group(**required_fields)
        return group, True

    async def get_group_by_telegram_id(self, telegram_id: int) -> Optional[Group]:
        try:
            result = await self.session.execute(
                select(Group).where(Group.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения группы: {e}")
            return None

    async def create_group(self, **kwargs) -> Optional[Group]:
        try:
            group = Group(**kwargs)
            self.session.add(group)
            await self.session.flush()
            return group
        except Exception as e:
            logger.error(f"Ошибка создания группы: {e}")
            return None

    async def is_user_in_group(self, user_id: int, group_id: int) -> bool:
        try:
            result = await self.session.execute(
                select(UserGroup).where(
                    UserGroup.user_id == user_id,
                    UserGroup.group_id == group_id,
                )
            )
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Ошибка проверки членства: {e}")
            return False

    async def add_user_to_group(self, user_id: int, group_id: int, is_moderator: bool = False) -> Tuple[bool, str]:
        if await self.is_user_in_group(user_id, group_id):
            return False, "Вы уже состоите в этой группе"
        try:
            user_group = UserGroup(
                user_id=user_id,
                group_id=group_id,
                is_moderator=is_moderator,
            )
            self.session.add(user_group)
            await self.session.flush()
            result = await self.session.execute(
                select(Group).where(Group.telegram_id == group_id)
            )
            group = result.scalar_one_or_none()
            if group:
                group.participants_count += 1
                await self.session.flush()
            return True, "Вы успешно добавлены в группу"
        except Exception as e:
            logger.error(f"Ошибка добавления в группу: {e}")
            await self.session.rollback()
            return False, f"Ошибка при добавлении в группу: {str(e)}"

    async def get_group_members(self, group_id: int) -> List[User]:
        try:
            result = await self.session.execute(
                select(User).join(UserGroup).where(UserGroup.group_id == group_id)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка получения участников группы: {e}")
            return []
