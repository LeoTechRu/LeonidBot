# /sd/tg/LeonidBot/core/services/telegram.py
import db
from logger import logger
from core.models import (
    User,
    Group,
    UserGroup,
    UserRole,
    LogSettings,
    LogLevel,
    GroupType,
)
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Tuple, Any
from datetime import datetime, timedelta
import os
from aiogram import Bot


class UserService:
    def __init__(self):
        self.admin_chat_id = None
        self.session = None

    async def __aenter__(self):
        self.session = db.async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self.session.commit()
        else:
            await self.session.rollback()
        await self.session.close()

    # ==== USER METHODS ====
    async def get_or_create_user(self, telegram_id: int, **kwargs) -> Tuple[User, bool]:
        """Получает или создает пользователя с автоматическим заполнением данных"""
        user = await self.get_user_by_telegram_id(telegram_id)
        if user:
            return user, False

        # Автоматическое заполнение из kwargs
        required_fields = {
            "telegram_id": telegram_id,
            "first_name": kwargs.get("first_name", f"User_{telegram_id}"),
            "role": kwargs.get("role", UserRole.single.value)
        }
        if "id" in kwargs:
            required_fields["id"] = kwargs["id"]

        # Добавляем опциональные поля
        optional_fields = {
            "username": kwargs.get("username"),
            "last_name": kwargs.get("last_name"),
            "language_code": kwargs.get("language_code"),
            "is_premium": kwargs.get("is_premium", False)
        }

        return await self.create_user(**{**required_fields, **optional_fields}), True

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получает пользователя из БД"""
        try:
            result = await self.session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None

    async def create_user(self, **kwargs) -> Optional[User]:
        """Создает нового пользователя в БД"""
        try:
            # Устанавливаем роль по умолчанию
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
        """Обновляет роль пользователя в БД"""
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

    # ==== GROUP METHODS ====
    async def get_or_create_group(self, telegram_id: int, **kwargs) -> Tuple[Group, bool]:
        """Получает или создает группу с автоматическим заполнением данных"""
        group = await self.get_group_by_telegram_id(telegram_id)
        if group:
            return group, False

        required_fields = {
            "telegram_id": telegram_id,
            "title": kwargs.get("title", f"Group_{telegram_id}"),
            "type": kwargs.get("type", GroupType.private),
            "owner_id": kwargs.get("owner_id", telegram_id)
        }

        return await self.create_group(**required_fields), True

    async def get_group_by_telegram_id(self, telegram_id: int) -> Optional[Group]:
        """Получает группу из БД"""
        try:
            result = await self.session.execute(
                select(Group).where(Group.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения группы: {e}")
            return None

    async def create_group(self, **kwargs) -> Optional[Group]:
        """Создает новую группу в БД"""
        try:
            group = Group(**kwargs)
            self.session.add(group)
            await self.session.flush()
            return group
        except Exception as e:
            logger.error(f"Ошибка создания группы: {e}")
            return None

    async def is_user_in_group(self, user_id: int, group_id: int) -> bool:
        """Проверяет членство в группе через БД"""
        try:
            result = await self.session.execute(
                select(UserGroup).where(
                    UserGroup.user_id == user_id,
                    UserGroup.group_id == group_id
                )
            )
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Ошибка проверки членства: {e}")
            return False

    async def add_user_to_group(self, user_id: int, group_id: int, is_moderator: bool = False) -> Tuple[bool, str]:
        """Добавляет пользователя в группу"""
        if await self.is_user_in_group(user_id, group_id):
            return False, "Вы уже состоите в этой группе"

        try:
            user_group = UserGroup(
                user_id=user_id,
                group_id=group_id,
                is_moderator=is_moderator
            )
            self.session.add(user_group)
            await self.session.flush()

            # Обновляем счетчик участников
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
        """Получает участников группы через БД"""
        try:
            result = await self.session.execute(
                select(User).join(UserGroup).where(UserGroup.group_id == group_id)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Ошибка получения участников группы: {e}")
            return []

    # ==== LOGGING METHODS ====
    async def get_log_settings(self) -> Optional[LogSettings]:
        """Получает настройки логирования из БД"""
        try:
            result = await self.session.execute(
                select(LogSettings).where(LogSettings.id == 1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения настроек логирования: {e}")
            return None

    async def update_log_level(self, level: LogLevel, chat_id: int = None) -> bool:
        """Обновляет уровень логирования в БД"""
        try:
            settings = await self.get_log_settings()
            if settings:
                settings.level = level
                settings.updated_at = datetime.utcnow()
                await self.session.flush()
                return True
            # Если настроек нет - создаем новые
            settings = LogSettings(
                id=1,
                level=level,
                chat_id=chat_id or self.admin_chat_id,  # Указываем chat_id текущего пользователя
                updated_at=datetime.utcnow()
            )
            self.session.add(settings)
            await self.session.flush()
            logger.setLevel(level.name)
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления уровня логирования: {e}")
            return False

    async def send_log_to_telegram(self, level: LogLevel, message: str):
        """Отправляет лог в Telegram с учетом уровня логирования"""
        try:
            settings = await self.get_log_settings()
            if not settings:
                return False
            # Проверяем уровень логирования
            if level.value < settings.level.value:
                return False
            # Отправляем сообщение
            bot = Bot(token=os.getenv("BOT_TOKEN"))
            await bot.send_message(
                chat_id=settings.chat_id,
                text=f"[{level.name}] {message}",
                parse_mode="MarkdownV2"
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки лога в Telegram: {e}")
            return False

