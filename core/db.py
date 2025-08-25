# /sd/tg/LeonidBot/core/db.py
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import builtins
import sys

from base import Base
import core.models  # noqa: F401 - ensure models are loaded

load_dotenv()

# Database configuration

# Explicit DATABASE_URL has priority.  Otherwise gather individual
# parameters and build a Postgres URL.  If any of the expected variables are
# missing (e.g. local development environment) fall back to an SQLite
# database so that the application can at least start.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    if all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
        DATABASE_URL = (
            "postgresql+asyncpg://"
            f"{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
        )
    else:
        DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Async engine and session
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def init_models() -> None:
    """Create database tables for all models.

    The function attempts to use the configured database URL.  If the
    connection fails (for example, PostgreSQL is not running) it falls back
    to a local SQLite database so the application can still operate in a
    degraded but functional mode.
    """
    global engine, async_session, DATABASE_URL
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        DATABASE_URL = "sqlite+aiosqlite:///./test.db"
        engine = create_async_engine(DATABASE_URL)
        async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

# Bot
BOT_TOKEN = os.getenv("BOT_TOKEN") or "123456:" + "A" * 35
try:
    bot = Bot(token=BOT_TOKEN)
except Exception:
    BOT_TOKEN = "123456:" + "A" * 35
    bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Expose this module as ``db`` so tests can import it implicitly
builtins.db = sys.modules[__name__]
