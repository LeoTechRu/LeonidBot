from db import async_session
from logger import logger
from models import User, UserRole
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Tuple


class UserService:
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

    async def get_or_create_user(self, telegram_id: int, **kwargs) -> Tuple[User, bool]:
        user = await self.get_user_by_telegram_id(telegram_id)
        if user:
            return user, False

        required_fields = {
            "telegram_id": telegram_id,
            "first_name": kwargs.get("first_name", f"User_{telegram_id}"),
            "role": kwargs.get("role", UserRole.single.value),
        }
        optional_fields = {
            "username": kwargs.get("username"),
            "last_name": kwargs.get("last_name"),
            "language_code": kwargs.get("language_code"),
            "is_premium": kwargs.get("is_premium", False),
        }
        user = await self.create_user(**{**required_fields, **optional_fields})
        return user, True

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        try:
            result = await self.session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None

    async def create_user(self, **kwargs) -> Optional[User]:
        try:
            if "role" not in kwargs or kwargs["role"] is None:
                kwargs["role"] = UserRole.single.value
            user = User(**kwargs)
            self.session.add(user)
            await self.session.flush()
            return user
        except IntegrityError as e:
            logger.error(f"IntegrityError при создании пользователя: {e}")
            await self.session.rollback()
            return await self.get_user_by_telegram_id(kwargs["telegram_id"])
        except Exception as e:
            logger.error(f"Неожиданная ошибка при создании пользователя: {e}")
            return None

    async def update_user_role(self, telegram_id: int, new_role: UserRole) -> bool:
        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            return False
        try:
            user.role = new_role.value
            await self.session.flush()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления роли пользователя: {e}")
            return False
