# /sd/tg/LeonidBot/bot/main.py
import asyncio
import logging

from aiogram.exceptions import TelegramNetworkError

from core.db import bot, dp
from bot.handlers.telegram import user_router, group_router, router
from core.logger import LoggerMiddleware


async def main() -> None:
    """Run bot polling with middleware and routers."""
    dp.message.middleware(LoggerMiddleware(bot))
    dp.callback_query.middleware(LoggerMiddleware(bot))
    dp.include_router(user_router)
    dp.include_router(group_router)
    dp.include_router(router)
    try:
        await dp.start_polling(bot)
    except TelegramNetworkError as e:
        logging.error(f"Telegram network error: {e}")


if __name__ == "__main__":
    asyncio.run(main())

