"""Database models used by the application."""
from enum import IntEnum, Enum as PyEnum

from .utils import utcnow

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    JSON,
)

from base import Base

__mapper_args__ = {
    "confirm_deleted_rows": False  # Для PostgreSQL
}


class UserRole(IntEnum):  # Числовая иерархия ролей
    ban = 0
    single = 1
    multiplayer = 2
    moderator = 3
    admin = 4


class GroupType(PyEnum):  # Типы групп и каналов
    private = "private"
    public = "public"
    group = "group"
    supergroup = "supergroup"
    channel = "channel"


class ChannelType(PyEnum):
    channel = "channel"
    supergroup = "supergroup"


class TgUser(Base):
    """Telegram user data stored separately from web accounts."""

    __tablename__ = "tg_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(32), unique=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10))
    role = Column(String(20), default=UserRole.single.name)
    bot_settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class WebUser(Base):
    """User registered via web interface."""

    __tablename__ = "web_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(255))
    phone = Column(String(20))
    full_name = Column(String(255))
    password_hash = Column(String(255))
    role = Column(String(20), default=UserRole.single.name)
    privacy_settings = Column(JSON, default=dict)
    telegram_user_id = Column(Integer, ForeignKey("tg_users.id"))
    birthday = Column(Date)
    language = Column(String(10))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Group(Base):  # Группа
    __tablename__ = "groups"

    id = Column(BigInteger, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(Enum(GroupType), default=GroupType.private)
    owner_id = Column(BigInteger, ForeignKey("tg_users.telegram_id"))
    description = Column(String(500))
    participants_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Channel(Base):  # Канал
    __tablename__ = "channels"

    id = Column(BigInteger, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(Enum(ChannelType), default=ChannelType.channel)
    owner_id = Column(BigInteger, ForeignKey("tg_users.telegram_id"))
    username = Column(String(32))
    participants_count = Column(Integer, default=0)
    description = Column(String(500))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class UserGroup(Base):  # Связь пользователь-группа (многие ко многим)
    __tablename__ = "user_group"

    user_id = Column(
        BigInteger, ForeignKey("tg_users.telegram_id"), primary_key=True
    )
    group_id = Column(
        BigInteger, ForeignKey("groups.telegram_id"), primary_key=True
    )
    is_owner = Column(Boolean, default=False)
    is_moderator = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=utcnow)


# ---------------------------------------------------------------------------
# Task model
# ---------------------------------------------------------------------------


class TaskStatus(PyEnum):
    """Possible statuses for :class:`Task`."""

    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class Task(Base):
    """Basic task item owned by a telegram user."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("tg_users.telegram_id"))
    title = Column(String(255), nullable=False)
    description = Column(String(500))
    due_date = Column(DateTime)
    status = Column(Enum(TaskStatus), default=TaskStatus.todo)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# Reminder model
# ---------------------------------------------------------------------------


class Reminder(Base):
    """Simple reminder item owned by a telegram user."""

    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("tg_users.telegram_id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    message = Column(String(500), nullable=False)
    remind_at = Column(DateTime, nullable=False)
    is_done = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# TimeEntry model
# ---------------------------------------------------------------------------


class TimeEntry(Base):
    """Time tracking entry for a telegram user."""

    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("tg_users.telegram_id"))
    start_time = Column(DateTime, default=utcnow, nullable=False)
    end_time = Column(DateTime)
    description = Column(String(500))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


# Модели для логгера:
class LogLevel(IntEnum):
    """Уровни логирования по аналогии со стандартным ``logging``.

    Значения указаны численно, чтобы корректно сравнивать уровни
    между собой (``DEBUG`` < ``INFO`` < ``ERROR``).
    """

    DEBUG = 10
    INFO = 20
    ERROR = 40


class LogSettings(Base):
    __tablename__ = "log_settings"

    id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)  # ID группы для логов
    level = Column(
        Enum(LogLevel), default=LogLevel.ERROR
    )  # Уровень логирования
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<LogSettings(level='{self.level}', chat_id='{self.chat_id}')>"
