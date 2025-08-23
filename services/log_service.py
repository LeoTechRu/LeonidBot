import os
from datetime import datetime
from aiogram import Bot
from db import async_session
from logger import logger
from models import LogSettings, LogLevel
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional


class LogService:
    def __init__(self, session: AsyncSession | None = None, admin_chat_id: int | None = None):
        self.session = session
        self.admin_chat_id = admin_chat_id
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

    async def get_log_settings(self) -> Optional[LogSettings]:
        try:
            result = await self.session.execute(
                select(LogSettings).where(LogSettings.id == 1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения настроек логирования: {e}")
            return None

    async def update_log_level(self, level: LogLevel, chat_id: int = None) -> bool:
        try:
            settings = await self.get_log_settings()
            if settings:
                settings.level = level
                settings.updated_at = datetime.utcnow()
                await self.session.flush()
                return True
            settings = LogSettings(
                id=1,
                level=level,
                chat_id=chat_id or self.admin_chat_id,
                updated_at=datetime.utcnow(),
            )
            self.session.add(settings)
            await self.session.flush()
            logger.setLevel(level.name)
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления уровня логирования: {e}")
            return False

    async def send_log_to_telegram(self, level: LogLevel, message: str) -> bool:
        try:
            settings = await self.get_log_settings()
            if not settings:
                return False
            if level.value < settings.level.value:
                return False
            bot = Bot(token=os.getenv("BOT_TOKEN"))
            await bot.send_message(
                chat_id=settings.chat_id,
                text=f"[{level.name}] {message}",
                parse_mode="MarkdownV2",
            )
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки лога в Telegram: {e}")
            return False
