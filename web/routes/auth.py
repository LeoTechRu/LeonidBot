from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Dict

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import db
from services.telegram import UserService


router = APIRouter(tags=["auth"])

# Configure templates relative to this file
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request, mode: str = "callback"):
    """Render Telegram Login widget page."""
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME") or os.getenv("BOT_USERNAME") or ""
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "bot_username": bot_username, "mode": mode},
    )


async def _validate_telegram_auth(data: Dict[str, str]) -> Dict[str, str]:
    """Validate Telegram login data using HMAC-SHA256."""
    received_hash = data.get("hash")
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing hash")

    auth_date = int(data.get("auth_date", "0"))
    if time.time() - auth_date > 86400:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth date too old")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items()) if k != "hash"
    )
    secret_key = hashlib.sha256((db.BOT_TOKEN or "").encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
    return data


@router.api_route("/callback", methods=["GET", "POST"])
async def auth_callback(request: Request):
    """Handle Telegram auth data."""
    if request.method == "POST":
        if request.headers.get("content-type", "").startswith("application/json"):
            params = dict(await request.json())
        else:
            params = dict(await request.form())
    else:
        params = dict(request.query_params)

    valid = await _validate_telegram_auth(params)
    telegram_id = int(valid["id"])

    async with UserService() as service:
        user, _ = await service.get_or_create_user(
            telegram_id,
            first_name=valid.get("first_name"),
            last_name=valid.get("last_name"),
            username=valid.get("username"),
            language_code=valid.get("language_code"),
        )

    response = JSONResponse({"status": "ok", "user": {"telegram_id": user.telegram_id}})
    response.set_cookie("telegram_id", str(user.telegram_id), max_age=86400, httponly=True)
    return response
