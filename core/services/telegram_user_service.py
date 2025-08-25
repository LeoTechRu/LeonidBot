"""Service layer for telegram-related database operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core import db
from core.logger import logger
from core.models import (
    TgUser,
    Group,
    UserGroup,
    UserRole,
    LogSettings,
    LogLevel,
    GroupType,
)
from core.utils import utcnow


class TelegramUserService:
    """CRUD helpers for ``TgUser`` and related models."""

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self.admin_chat_id = None
        self._external = session is not None

    async def __aenter__(self) -> "TelegramUserService":
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

    # ------------------------------------------------------------------
    # User helpers
    # ------------------------------------------------------------------
    def determine_role(
        self, telegram_id: int, role: UserRole | str | None = None
    ) -> UserRole:
        if role is not None:
            return role if isinstance(role, UserRole) else UserRole[role]
        from web.config import S

        admin_ids = [
            int(x)
            for x in (S.ADMIN_IDS or "").split(",")
            if x.strip().isdigit()
        ]
        return UserRole.admin if telegram_id in admin_ids else UserRole.single

    async def get_user_by_telegram_id(
        self, telegram_id: int
    ) -> Optional[TgUser]:
        result = await self.session.execute(
            select(TgUser).where(TgUser.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create_user(self, **kwargs) -> Optional[TgUser]:
        try:
            if "role" not in kwargs or kwargs["role"] is None:
                kwargs["role"] = UserRole.single.name
            user = TgUser(**kwargs)
            self.session.add(user)
            await self.session.flush()
            return user
        except IntegrityError as e:
            logger.error(f"IntegrityError при создании пользователя: {e}")
            await self.session.rollback()
            return await self.get_user_by_telegram_id(kwargs["telegram_id"])
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Неожиданная ошибка при создании пользователя: {e}")
            return None

    async def get_or_create_user(
        self,
        telegram_id: int,
        *,
        role: UserRole | str | None = None,
        **kwargs,
    ) -> Tuple[TgUser, bool]:
        user = await self.get_user_by_telegram_id(telegram_id)
        if user:
            return user, False

        resolved_role = self.determine_role(telegram_id, role)
        required_fields = {
            "telegram_id": telegram_id,
            "first_name": kwargs.get("first_name", f"User_{telegram_id}"),
            "role": resolved_role.name,
        }

        optional_fields = {
            "username": kwargs.get("username"),
            "last_name": kwargs.get("last_name"),
            "language_code": kwargs.get("language_code"),
        }

        user = await self.create_user(**{**required_fields, **optional_fields})
        return user, True

    async def update_from_telegram(
        self, telegram_id: int, **data: Any
    ) -> TgUser:
        """Create or update a telegram user from Telegram login data."""

        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            user = TgUser(telegram_id=telegram_id, role=UserRole.single.name)
            self.session.add(user)
        for field in ["username", "first_name", "last_name", "language_code"]:
            if field in data and data[field] is not None:
                setattr(user, field, data[field])
        user.updated_at = utcnow()
        await self.session.flush()
        return user

    async def update_user_role(
        self, telegram_id: int, new_role: UserRole
    ) -> bool:
        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            return False
        try:
            user.role = new_role.name
            await self.session.flush()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления роли пользователя: {e}")
            return False

    async def list_users(self) -> List[TgUser]:
        result = await self.session.execute(select(TgUser))
        return result.scalars().all()

    # ------------------------------------------------------------------
    # Group helpers
    # ------------------------------------------------------------------
    async def get_group_by_telegram_id(
        self, telegram_id: int
    ) -> Optional[Group]:
        result = await self.session.execute(
            select(Group).where(Group.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create_group(self, **kwargs) -> Optional[Group]:
        try:
            group = Group(**kwargs)
            self.session.add(group)
            await self.session.flush()
            return group
        except Exception as e:
            logger.error(f"Ошибка создания группы: {e}")
            return None

    async def get_or_create_group(
        self, telegram_id: int, **kwargs
    ) -> Tuple[Group, bool]:
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

    async def is_user_in_group(self, user_id: int, group_id: int) -> bool:
        result = await self.session.execute(
            select(UserGroup).where(
                UserGroup.user_id == user_id, UserGroup.group_id == group_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_user_to_group(
        self, user_id: int, group_id: int, is_moderator: bool = False
    ) -> Tuple[bool, str]:
        if await self.is_user_in_group(user_id, group_id):
            return False, "Вы уже состоите в этой группе"
        try:
            link = UserGroup(
                user_id=user_id, group_id=group_id, is_moderator=is_moderator
            )
            self.session.add(link)
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

    async def get_group_members(self, group_id: int) -> List[TgUser]:
        result = await self.session.execute(
            select(TgUser)
            .join(UserGroup)
            .where(UserGroup.group_id == group_id)
        )
        return result.scalars().all()

    async def list_user_groups(self, user_id: int) -> List[Group]:
        result = await self.session.execute(
            select(Group).join(UserGroup).where(UserGroup.user_id == user_id)
        )
        return result.scalars().all()

    async def get_user_and_groups(
        self, telegram_id: int
    ) -> Tuple[Optional[TgUser], List[Group]]:
        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None, []
        groups = await self.list_user_groups(telegram_id)
        return user, groups

    async def get_contact_info(self, telegram_id: int) -> Dict[str, Any]:
        user, groups = await self.get_user_and_groups(telegram_id)
        if not user:
            return {}
        display_name = (
            user.bot_settings.get("full_display_name")
            if isinstance(user.bot_settings, dict)
            else None
        ) or f"{user.first_name} {user.last_name or ''}".strip()
        return {
            "user": user,
            "groups": groups,
            "telegram_id": user.telegram_id,
            "username": f"@{user.username}" if user.username else None,
            "full_display_name": display_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "display_name": display_name,
            "email": (
                user.bot_settings.get("email")
                if isinstance(user.bot_settings, dict)
                else None
            ),
            "phone": (
                user.bot_settings.get("phone")
                if isinstance(user.bot_settings, dict)
                else None
            ),
            "birthday": (
                user.bot_settings.get("birthday")
                if isinstance(user.bot_settings, dict)
                else None
            ),
            "language_code": user.language_code,
            "role_name": user.role,
        }

    async def update_full_display_name(
        self, telegram_id: int, name: str
    ) -> bool:
        """Update user's custom display name stored in ``bot_settings``."""

        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            return False
        existing = (
            user.bot_settings if isinstance(user.bot_settings, dict) else {}
        )
        user.bot_settings = {**existing, "full_display_name": name}
        user.updated_at = utcnow()
        await self.session.flush()
        return True

    async def update_user_profile(
        self, telegram_id: int, data: Dict[str, Any]
    ) -> Optional[TgUser]:
        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            return None
        allowed = {
            "first_name",
            "last_name",
            "username",
            "language_code",
            "bot_settings",
        }
        for field, value in data.items():
            if field in allowed and value is not None:
                setattr(user, field, value)
        user.updated_at = utcnow()
        await self.session.flush()
        return user

    async def list_groups_with_members(self) -> List[Dict[str, Any]]:
        result = await self.session.execute(select(Group))
        groups = result.scalars().all()
        data: List[Dict[str, Any]] = []
        for group in groups:
            members = await self.get_group_members(group.telegram_id)
            data.append({"group": group, "members": members})
        return data

    # ------------------------------------------------------------------
    # Logging settings
    # ------------------------------------------------------------------
    async def get_log_settings(self) -> Optional[LogSettings]:
        result = await self.session.execute(
            select(LogSettings).where(LogSettings.id == 1)
        )
        return result.scalar_one_or_none()

    async def update_log_level(
        self, level: LogLevel, chat_id: int | None = None
    ) -> bool:
        try:
            settings = await self.get_log_settings()
            if settings:
                settings.level = level
                settings.updated_at = utcnow()
                await self.session.flush()
                return True
            settings = LogSettings(
                id=1,
                level=level,
                chat_id=chat_id or self.admin_chat_id,
                updated_at=utcnow(),
            )
            self.session.add(settings)
            await self.session.flush()
            logger.setLevel(level.name)
            return True
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Ошибка обновления уровня логирования: {e}")
            return False

    async def send_log_to_telegram(
        self, level: LogLevel, message: str
    ) -> bool:
        try:
            settings = await self.get_log_settings()
            if not settings or level.value < settings.level.value:
                return False
            bot = Bot(token=db.BOT_TOKEN)
            await bot.send_message(
                chat_id=settings.chat_id,
                text=f"[{level.name}] {message}",
                parse_mode="MarkdownV2",
            )
            return True
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Ошибка отправки лога в Telegram: {e}")
            return False
