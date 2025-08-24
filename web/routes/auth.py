from __future__ import annotations
import hmac, hashlib, time
from typing import Dict
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from urllib.parse import quote
from web.config import S
from core.services.telegram import UserService

router = APIRouter(tags=["auth"])

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

def verify_telegram_login(data: Dict[str, str]) -> bool:
    recv_hash = data.get("hash", "")
    pairs = [f"{k}={v}" for k, v in sorted(data.items()) if k != "hash"]
    data_check_string = "\n".join(pairs)
    secret = hashlib.sha256(S.BOT_TOKEN.encode()).digest()
    calc_hash = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calc_hash, recv_hash):
        return False
    try:
        auth_date = int(data.get("auth_date", "0"))
    except ValueError:
        return False
    return auth_date > 0 and (time.time() - auth_date) <= S.SESSION_MAX_AGE

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str | None = None) -> HTMLResponse:
    """Render login page with Telegram widget."""
    bot_user = S.TELEGRAM_BOT_USERNAME
    next_query = f"?next={quote(next, safe='')}" if next else ""
    return templates.TemplateResponse(
        request,
        "auth/login.html",
        {"bot_username": bot_user, "next_query": next_query},
    )

@router.post("/callback")
async def telegram_callback(request: Request, next: str | None = None):
    data = dict((await request.form()).items())
    if not verify_telegram_login(data):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad Telegram signature")
    telegram_id = int(data["id"])  # type: ignore[index]

    async with UserService() as service:
        role = service.determine_role(telegram_id)
        user, created = await service.get_or_create_user(
            telegram_id,
            role=role,
            id=telegram_id,
            first_name=data.get("first_name"),
            username=data.get("username"),
            last_name=data.get("last_name"),
            language_code=data.get("language_code"),
        )
        if not created and user and user.role != role.value:
            await service.update_user_role(telegram_id, role)

    target = next if next and next.startswith("/") else "/start"
    response = RedirectResponse(target, status_code=303)
    response.set_cookie(
        "telegram_id",
        str(telegram_id),
        max_age=S.SESSION_MAX_AGE,
        path="/",
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse("/auth/login", status_code=303)
    response.delete_cookie("telegram_id", path="/")
    return response
