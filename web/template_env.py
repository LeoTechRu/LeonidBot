from __future__ import annotations

from pathlib import Path
import os

from fastapi.templating import Jinja2Templates

from .config import S

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

_web_url = os.getenv("WEB_PUBLIC_URL") or (
    str(S.WEB_PUBLIC_URL) if S.WEB_PUBLIC_URL else "https://leonid.pro"
)
_bot_username = os.getenv("BOT_USERNAME", S.BOT_USERNAME)
_bot_username_with_at = "@" + _bot_username.lstrip("@")

templates.env.globals.update(
    APP_BRAND_NAME=S.APP_BRAND_NAME,
    WEB_PUBLIC_URL=S.WEB_PUBLIC_URL,
    BOT_LANDING_URL=S.BOT_LANDING_URL,
    TG_LOGIN_ENABLED=S.TG_LOGIN_ENABLED,
    TG_BOT_USERNAME=S.BOT_USERNAME,
    BOT_USERNAME=("@" + (S.BOT_USERNAME or "").lstrip("@")) if S.BOT_USERNAME else None,
    RECAPTCHA_SITE_KEY=S.RECAPTCHA_SITE_KEY,
    CALENDAR_V2_ENABLED=S.CALENDAR_V2_ENABLED,
)

__all__ = ["templates"]
