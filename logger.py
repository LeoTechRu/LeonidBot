# /sd/tg/LeonidBot/logger.py
from datetime import datetime

from aiogram import BaseMiddleware, Bot
from aiogram.types import Update, Message, CallbackQuery
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.exc import SQLAlchemyError
from typing import Callable, Dict, Any, Optional
import logging
import os
from models import LogLevel
from web.dependencies import get_session

# Настройка базового логгера (только консоль)
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("LeonidBot")

def escape_markdown_v2(text: str) -> str:
    """Экранирует специальные символы MarkdownV2"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{c}' if c in escape_chars else c for c in text)

class LoggerMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.admin_chat_id = int(os.getenv("ADMIN_CHAT_ID", 0))

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Any],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        try:
            # Логируем событие
            await self._log_event(event)

            # Вызываем обработчик
            return await handler(event, data)

        except TelegramAPIError as e:
            await self._handle_telegram_error(event, e)

        except SQLAlchemyError as e:
            await self._handle_database_error(event, e)

        except Exception as e:
            await self._handle_unexpected_error(event, e)

    async def _log_event(self, event: Update):
        """Логирование события с детализацией"""
        try:
            if isinstance(event, Message):
                await self._log(
                    LogLevel.DEBUG,
                    f"[EVENT:Message] Текст: {event.text or '[MEDIA]'}",
                    event=event
                )
            elif isinstance(event, CallbackQuery):
                await self._log(
                    LogLevel.DEBUG,
                    f"[EVENT:Callback] Данные: {event.data}",
                    event=event
                )
            else:
                await self._log(
                    LogLevel.DEBUG,
                    f"[EVENT:Unknown] Тип: {type(event)}",
                    event=event
                )
        except Exception as e:
            logger.error(f"Ошибка логирования события: {e}", exc_info=True)

    async def _handle_telegram_error(self, event: Update, error: TelegramAPIError):
        """Обработка Telegram API ошибок"""
        await self._log(
            LogLevel.ERROR,
            f"[Telegram API ошибка]: {error}",
            event=event,
            exc_info=True
        )
        try:
            await self._send_error_message(event, "Ошибка связи с Telegram. Администратор уже уведомлен.")
        except:
            logger.warning("Не удалось отправить сообщение пользователю при Telegram API ошибке")

    async def _handle_database_error(self, event: Update, error: SQLAlchemyError):
        """Обработка ошибок базы данных"""
        await self._log(
            LogLevel.ERROR,
            f"[База данных ошибка]: {error}",
            event=event,
            exc_info=True
        )
        try:
            await self._send_error_message(event, "Ошибка базы данных. Администратор уже уведомлен")
        except:
            pass

    async def _handle_unexpected_error(self, event: Update, error: Exception):
        """Обработка неожиданных ошибок"""
        await self._log(
            LogLevel.ERROR,
            f"[Неизвестная ошибка]: {error}",
            event=event,
            exc_info=True
        )
        try:
            await self._send_error_message(event, "Произошла внутренняя ошибка. Администратор уже уведомлен")
        except:
            pass

    async def _log(
            self,
            level: LogLevel,
            message: str,
            event: Optional[Update] = None,
            exc_info: bool = False
    ):
        """Центральная точка логирования с отправкой в Telegram"""
        # Логируем в консоль
        if level == LogLevel.DEBUG:
            logger.debug(message, exc_info=exc_info)
        elif level == LogLevel.INFO:
            logger.info(message, exc_info=exc_info)
        elif level == LogLevel.ERROR:
            logger.error(message, exc_info=exc_info)

        # Отправляем в Telegram только если уровень соответствует настройкам
        try:
            from services.telegram import UserService
            async with get_session() as session:
                async with UserService(session) as user_service:
                    settings = await user_service.get_log_settings()
                    current_level = settings.level if settings else LogLevel.DEBUG
                    chat_id = settings.chat_id if settings else self.admin_chat_id

                    # Проверяем, нужно ли отправлять лог
                    if level.value < current_level.value:
                        return

                    # Формируем сообщение
                    formatted_message = (
                        f"[{level.name}] "
                        f"{message}\n"
                        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    # Экранируем специальные символы MarkdownV2
                    escaped_message = escape_markdown_v2(formatted_message)
                    # Отправляем в Telegram
                    if chat_id:
                        await self.bot.send_message(
                            chat_id=chat_id,
                            text=escaped_message,
                            parse_mode="MarkdownV2"
                        )
        except Exception as e:
            logger.critical(f"Критическая ошибка отправки лога в Telegram: {e}")

    async def _send_error_message(self, event: Update, text: str):
        """Отправка сообщения об ошибке пользователю"""
        chat_id = self._extract_chat_id(event)
        if chat_id:
            try:
                await self.bot.send_message(chat_id, text)
            except TelegramAPIError as e:
                logger.warning(f"Не удалось отправить сообщение пользователю {chat_id}: {e}")

    def _extract_chat_id(self, event: Update) -> Optional[int]:
        """Извлекает chat_id из события"""
        if isinstance(event, Message):
            return event.chat.id
        elif isinstance(event, CallbackQuery) and event.message:
            return event.message.chat.id
        elif hasattr(event, "message") and event.message:
            return event.message.chat.id
        return None
