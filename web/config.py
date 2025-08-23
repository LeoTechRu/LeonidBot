from __future__ import annotations
from pydantic_settings import BaseSettings
from pydantic import Field, AnyHttpUrl, validator
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Всегда грузим КОРНЕВОЙ .env (repo root), даже если uvicorn запущен из другого cwd
_root_env = find_dotenv(usecwd=False)
if _root_env:
    load_dotenv(_root_env, override=False)


class Settings(BaseSettings):
    BOT_TOKEN: str = Field(..., description="Telegram bot token")
    TELEGRAM_BOT_USERNAME: str = Field(..., description="Bot username без @")
    PUBLIC_BASE_URL: AnyHttpUrl | None = None   # например, https://bot.example.com
    SESSION_MAX_AGE: int = 86400

    @validator("TELEGRAM_BOT_USERNAME")
    def strip_at(cls, v: str) -> str:
        return v.lstrip("@").strip()

    class Config:
        # дублируем чтение из root .env для pydantic (загружено выше через load_dotenv)
        env_file = _root_env if _root_env else ".env"
        case_sensitive = True


S = Settings()
