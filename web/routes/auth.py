import os
import time
import hmac
import hashlib
from typing import Dict

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import db
from services.telegram import UserService

router = APIRouter(tags=["auth"])

# Configure templates relative to this file
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)


async def _verify_telegram_data(data: Dict[str, str]) -> bool:
    """Verify data received from Telegram login widget.

    The signature is calculated by concatenating all key-value pairs
    (except ``hash``) sorted by keys separated with ``\n`` and then
    creating an HMAC-SHA256 using ``SHA256(BOT_TOKEN)`` as the secret.
    """
    received_hash = data.get("hash", "")
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()) if k != "hash")
    secret_key = hashlib.sha256(db.BOT_TOKEN.encode()).digest()
    calculated_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calculated_hash, received_hash)


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    """Render a page with Telegram Login widget."""
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "")
    return templates.TemplateResponse(
        "auth/login.html", {"request": request, "bot_username": bot_username}
    )


@router.post("/callback")
async def auth_callback(request: Request):
    """Handle Telegram auth callback verifying the data and creating a user."""
    # Support both query params and JSON/form body
    if request.headers.get("content-type", "").startswith("application/json"):
        payload = await request.json()
    else:
        try:
            form = await request.form()
            payload = dict(form)
        except Exception:
            payload = dict(request.query_params)

    if not await _verify_telegram_data(payload):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    auth_date = int(payload.get("auth_date", 0))
    if int(time.time()) - auth_date > 86400:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Auth expired")

    telegram_id = int(payload.get("id"))
    async with UserService() as service:
        user, _ = await service.get_or_create_user(
            telegram_id,
            first_name=payload.get("first_name"),
            last_name=payload.get("last_name"),
            username=payload.get("username"),
        )

    response = JSONResponse({"status": "ok", "user_id": user.telegram_id})
    # Persist user id for subsequent requests
    response.set_cookie("telegram_id", str(user.telegram_id), max_age=86400, httponly=True)
    return response
