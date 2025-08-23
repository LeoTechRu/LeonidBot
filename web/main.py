from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Dict

from fastapi import FastAPI, HTTPException, Request, Response

from core.db import BOT_TOKEN
from core.services.telegram import UserService
from .routes import profile, admin


app = FastAPI()
# Подключаем основные роутеры приложения
app.include_router(profile.router)
app.include_router(admin.router, prefix="/admin")


def _verify_telegram_auth(data: Dict[str, str]) -> bool:
    """Validate Telegram login widget data using the bot token."""
    received_hash = data.get("hash")
    if not received_hash:
        return False

    data_check = {k: v for k, v in data.items() if k != "hash"}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_check.items()))
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_hash, received_hash)


def _create_session(telegram_id: int) -> str:
    """Create a simple signed session token storing the telegram_id."""
    payload = json.dumps({"telegram_id": telegram_id})
    signature = hmac.new(BOT_TOKEN.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(payload.encode()).decode() + "." + signature
    return token


@app.get("/auth/telegram")
async def auth_telegram(request: Request, response: Response) -> Dict[str, bool]:
    """Authenticate user via Telegram login widget."""
    params = dict(request.query_params)
    if not _verify_telegram_auth(params):
        raise HTTPException(status_code=403, detail="Invalid hash")

    telegram_id = int(params["id"])
    async with UserService() as service:
        await service.get_or_create_user(
            telegram_id=telegram_id,
            first_name=params.get("first_name"),
            last_name=params.get("last_name"),
            username=params.get("username"),
        )

    response.set_cookie("session", _create_session(telegram_id), httponly=True)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web.main:app", host="0.0.0.0", port=8000)

