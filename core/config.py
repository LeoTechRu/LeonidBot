"""Application configuration using Pydantic settings."""
from __future__ import annotations
try:  # Pydantic v2
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover - fall back for environments with pydantic v1
    from pydantic import BaseSettings  # type: ignore


class Settings(BaseSettings):
    """Base application settings loaded from environment variables."""

    bot_token: str = ""  # Telegram bot token
    db_user: str = ""  # Database username
    db_password: str = ""  # Database password
    db_host: str = ""  # Database host
    db_name: str = ""  # Database name
    admin_chat_id: int = 0  # Telegram chat id for admin notifications

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
