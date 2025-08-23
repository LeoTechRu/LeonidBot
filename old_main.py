# /sd/tg/LeonidBot/main.py

# from aiogram.filters import Command
# from aiogram.types import Message
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
# Note: legacy file; updated import for new service structure
from services import UserService
from db import db
from handlers.telegram import user_router, group_router, TelegramMiddleware, setup_dispatcher
from datetime import datetime
from models import LogSettings

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = setup_dispatcher(bot)

async def main():
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            await db.create_all()
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
            break
        except TelegramNetworkError as e:
            retry_count += 1
            logger.error(f"Сетевая ошибка (попытка {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                await asyncio.sleep(5)
            else:
                # Уведомление админа о критической ошибке
                await bot.send_message(
                    chat_id=int(os.getenv("ADMIN_CHAT_ID", 0)),
                    text="Бот остановлен из-за сетевых проблем"
                )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())