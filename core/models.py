"""Database models used by the application."""
from enum import IntEnum, Enum as PyEnum
from datetime import date
from uuid import uuid4

from .db import bcrypt

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
    Float,
    String,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

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

    __tablename__ = "users_tg"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(32), unique=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    language_code = Column(String(10))
    role = Column(String(20), default=UserRole.single.name)
    bot_settings = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class WebUser(Base):
    """User registered via web interface."""

    __tablename__ = "users_web"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(255))
    phone = Column(String(20))
    full_name = Column(String(255))
    password_hash = Column(String(255))
    role = Column(String(20), default=UserRole.single.name)
    privacy_settings = Column(JSON, default=dict)
    birthday = Column(Date)
    language = Column(String(10))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    telegram_accounts = relationship(
        "TgUser",
        secondary="users_web_tg",
        backref="web_accounts",
    )

    # Flask-Login compatibility helpers
    @property
    def is_authenticated(self) -> bool:
        """All persisted web users are considered authenticated."""
        return True

    @property
    def is_active(self) -> bool:
        """User is active unless explicitly banned."""
        return self.role != UserRole.ban.name

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)

    def check_password(self, password: str) -> bool:
        """Validate password against stored bcrypt hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def avatar_url(self) -> str | None:
        """Optional avatar URL for header/profile.

        Looks into `privacy_settings["avatar_url"]` when present.
        Returns None if not set, letting templates fall back to a default icon.
        """
        try:
            if self.privacy_settings and isinstance(self.privacy_settings, dict):
                url = self.privacy_settings.get("avatar_url")
                if url:
                    return url
        except Exception:
            pass
        return None


class WebTgLink(Base):
    """Link between web users and their Telegram accounts."""

    __tablename__ = "users_web_tg"

    id = Column(Integer, primary_key=True, autoincrement=True)
    web_user_id = Column(Integer, ForeignKey("users_web.id"), nullable=False)
    tg_user_id = Column(Integer, ForeignKey("users_tg.id"), unique=True, nullable=False)
    link_type = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=utcnow)


class UserFavorite(Base):
    """Custom user navigation shortcuts."""

    __tablename__ = "users_favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("users_web.id"), nullable=False)
    label = Column(String(40))
    path = Column(String(128), nullable=False)
    position = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("owner_id", "path"),
        Index("ix_users_favorites_owner_position", "owner_id", "position"),
    )

class Group(Base):  # Группа
    __tablename__ = "groups"

    id = Column(BigInteger, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(Enum(GroupType), default=GroupType.private)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    description = Column(String(500))
    participants_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Channel(Base):  # Канал
    __tablename__ = "channels"

    id = Column(BigInteger, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(Enum(ChannelType), default=ChannelType.channel)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    username = Column(String(32))
    participants_count = Column(Integer, default=0)
    description = Column(String(500))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class UserGroup(Base):  # Связь пользователь-группа (многие ко многим)
    __tablename__ = "user_group"

    user_id = Column(
        BigInteger, ForeignKey("users_tg.telegram_id"), primary_key=True
    )
    group_id = Column(
        BigInteger, ForeignKey("groups.telegram_id"), primary_key=True
    )
    is_owner = Column(Boolean, default=False)
    is_moderator = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), default=utcnow)


# ---------------------------------------------------------------------------
# Task model
# ---------------------------------------------------------------------------

class TaskStatus(PyEnum):
    """Possible statuses for :class:`Task`."""
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


# PARA/PKM enums
class ContainerType(PyEnum):
    project = "project"
    area = "area"
    resource = "resource"


class ProjectStatus(PyEnum):
    active = "active"
    paused = "paused"
    completed = "completed"


class ActivityType(PyEnum):
    work = "work"
    learning = "learning"
    admin = "admin"
    rest = "rest"
    break_ = "break"


class TimeSource(PyEnum):
    timer = "timer"
    manual = "manual"
    import_ = "import"


class Task(Base):
    """Basic task item owned by a telegram user."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    title = Column(String(255), nullable=False)
    description = Column(String(500))
    due_date = Column(DateTime(timezone=True))
    status = Column(Enum(TaskStatus), default=TaskStatus.todo)

    # NexusCore-inspired поля
    cognitive_cost = Column(Integer)
    neural_priority = Column(Float)
    repeat_config = Column(JSON, default=dict)
    recurrence = Column(String(50))
    excluded_dates = Column(JSON, default=list)
    custom_properties = Column(JSON, default=dict)
    schedule_type = Column(String(50))
    reschedule_count = Column(Integer, default=0)

    checkpoints = relationship(
        "TaskCheckpoint", backref="task", cascade="all, delete-orphan"
    )
    exceptions = relationship(
        "ScheduleException", backref="task", cascade="all, delete-orphan"
    )
    # Link to time tracking entries (work logs)
    time_entries = relationship(
        "TimeEntry", backref="task", cascade="all, delete-orphan"
    )

    # PARA links
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    estimate_minutes = Column(Integer)

    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


# ---------------------------------------------------------------------------
# Reminder model
# ---------------------------------------------------------------------------

class Reminder(Base):
    """Simple reminder item owned by a telegram user."""

    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    message = Column(String(500), nullable=False)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    is_done = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


# ---------------------------------------------------------------------------
# CalendarEvent model
# ---------------------------------------------------------------------------

class CalendarEvent(Base):
    """Calendar event item owned by a telegram user."""

    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    title = Column(String(255), nullable=False)
    start_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    end_at = Column(DateTime(timezone=True))
    description = Column(String(500))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


# ---------------------------------------------------------------------------
# TimeEntry model
# ---------------------------------------------------------------------------

class TimeEntry(Base):
    """Time tracking entry for a telegram user."""

    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    # Optional link to a task: time tracking is work on a task
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    start_time = Column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    end_time = Column(DateTime(timezone=True))
    description = Column(String(500))
    # PARA inheritance fields
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True)
    activity_type = Column(Enum(ActivityType), default=ActivityType.work)
    billable = Column(Boolean, default=True)
    source = Column(Enum(TimeSource), default=TimeSource.timer)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # Convenience: computed duration in seconds (Python-side)
    @property
    def duration_seconds(self) -> int | None:
        """Return duration in seconds if entry is finished, else None."""
        if not self.start_time or not self.end_time:
            return None
        try:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds())
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Extended NexusCore-inspired models (сохранены целиком)
# ---------------------------------------------------------------------------

class AreaType(PyEnum):
    career = "CAREER"
    health = "HEALTH"
    education = "EDUCATION"
    finance = "FINANCE"
    personal = "PERSONAL"


class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    name = Column(String(255), nullable=False)
    type = Column(Enum(AreaType))
    color = Column(String(7))
    context_map = Column(JSON, default=dict)
    review_interval = Column(Integer)
    review_interval_days = Column(Integer, default=7)
    is_active = Column(Boolean, default=True)
    archived_at = Column(DateTime(timezone=True))
    # Tree fields
    parent_id = Column(Integer, ForeignKey("areas.id", ondelete="SET NULL"))
    mp_path = Column(String, default="", nullable=False)
    depth = Column(Integer, default=0, nullable=False)
    slug = Column(String, nullable=False, default="")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    cognitive_cost = Column(Integer)
    neural_priority = Column(Float)
    schedule = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.active)
    slug = Column(String(255))
    archived_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    schedule = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    frequency = Column(String(20), default="daily")
    progress = Column(JSON, default=dict)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    def toggle_progress(self, day: date) -> None:
        today = date.today()
        if day != today:
            raise ValueError("Can only toggle progress for today")
        key = day.isoformat()
        self.progress = self.progress or {}
        self.progress[key] = not self.progress.get(key, False)


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    title = Column(String(255), nullable=False)
    content = Column(String(2000))
    type = Column(String(50))
    meta = Column(JSON, default=dict)
    archived_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


# ---------------------------------------------------------------------------
# Note model (сохранено из ветки main)
# ---------------------------------------------------------------------------

class Note(Base):
    """Simple note item owned by a telegram user."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    title = Column(String(255))
    content = Column(Text, nullable=False)
    container_type = Column(Enum(ContainerType))
    container_id = Column(Integer)
    archived_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Archive(Base):
    __tablename__ = "archives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    source_type = Column(String(50))
    source_id = Column(Integer)
    archived_at = Column(DateTime, default=utcnow)


class TaskCheckpoint(Base):
    __tablename__ = "task_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    name = Column(String(255))
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)


class ScheduleException(Base):
    __tablename__ = "schedule_exceptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    date = Column(Date)
    reason = Column(String(255))


class OKRStatus(PyEnum):
    pending = "pending"
    active = "active"
    completed = "completed"


class OKR(Base):
    __tablename__ = "okrs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    objective = Column(String(255), nullable=False)
    description = Column(String(500))
    status = Column(Enum(OKRStatus), default=OKRStatus.pending)
    period_start = Column(Date)
    period_end = Column(Date)
    confidence = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    key_results = relationship(
        "KeyResult", backref="okr", cascade="all, delete-orphan"
    )


class MetricType(PyEnum):
    count = "count"
    binary = "binary"
    percent = "percent"


class KeyResult(Base):
    __tablename__ = "key_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    okr_id = Column(Integer, ForeignKey("okrs.id"))
    description = Column(String(255), nullable=False)
    metric_type = Column(Enum(MetricType))
    weight = Column(Float, default=1.0)
    target_value = Column(Float)
    current_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Interface(Base):
    __tablename__ = "interfaces"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    name = Column(String(255), nullable=False)
    config = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class Limit(Base):
    __tablename__ = "limits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("users_tg.telegram_id"))
    resource = Column(String(50), nullable=False)
    value = Column(Integer, nullable=False)
    expires_at = Column(DateTime)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    level = Column(Integer, default=0)
    description = Column(String(255))


class Perm(Base):
    __tablename__ = "perms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))


class UserRoleLink(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users_web.id"))
    role_id = Column(Integer, ForeignKey("roles.id"))
    expires_at = Column(DateTime)


class LinkType(PyEnum):
    hierarchy = "hierarchy"
    reference = "reference"
    dependency = "dependency"
    attachment = "attachment"
    temporal = "temporal"
    metadata = "metadata"


class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(50))
    source_id = Column(Integer)
    target_type = Column(String(50))
    target_id = Column(Integer)
    link_type = Column(Enum(LinkType))
    weight = Column(Float, default=1.0)
    decay = Column(Float, default=1.0)
    created_at = Column(DateTime, default=utcnow)


# ---------------------------------------------------------------------------
# Модели для логгера
# ---------------------------------------------------------------------------

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
    updated_at = Column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<LogSettings(level='{self.level}', chat_id='{self.chat_id}')>"


# ---------------------------------------------------------------------------
# Project notifications
# ---------------------------------------------------------------------------


class NotificationTrigger(Base):
    """Scheduled notification for a project."""

    __tablename__ = "triggers"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id = Column(PGUUID(as_uuid=True), nullable=False)
    channel_id = Column(PGUUID(as_uuid=True), nullable=False)
    next_fire_at = Column(DateTime(timezone=True), nullable=False)
    alarm_id = Column(PGUUID(as_uuid=True))
    rule = Column(JSON)
    dedupe_key = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class SentNotification(Base):
    """Log of sent notifications to ensure idempotency."""

    __tablename__ = "notifications"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    dedupe_key = Column(String(255), unique=True, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=utcnow)
