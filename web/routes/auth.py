from __future__ import annotations
import hmac, hashlib, time
from typing import Dict
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from web.config import S
from core.services.telegram import UserService

router = APIRouter(tags=["auth"])


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
async def login_page():
    # Telegram проверяет домен страницы против установленного в @BotFather (/setdomain).
    # Здесь важно корректное имя бота:
    bot_user = S.TELEGRAM_BOT_USERNAME
    html = f"""
<!doctype html><meta charset="utf-8">
<title>Login via Telegram</title>
<script async src="https://telegram.org/js/telegram-widget.js?22"
        data-telegram-login="{bot_user}"
        data-size="large"
        data-onauth="onTelegramAuth(user)"
        data-request-access="write"></script>
<script>
async function onTelegramAuth(user) {{
  const form = new URLSearchParams();
  for (const [k, v] of Object.entries(user)) form.append(k, v);
  const resp = await fetch("/auth/callback", {{
    method: "POST",
    headers: {{ "Content-Type": "application/x-www-form-urlencoded" }},
    body: form.toString()
  }});
  if (resp.redirected) {{
    window.location = resp.url;
  }} else {{
    const j = await resp.json();
    if (resp.ok) window.location = "/admin";
    else alert("Auth error: " + j.detail);
  }}
}}
</script>
<body><h1>Вход через Telegram</h1></body>
"""
    return HTMLResponse(html)


@router.post("/callback")
async def telegram_callback(request: Request):
    data = dict((await request.form()).items())
    if not verify_telegram_login(data):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad Telegram signature")

    telegram_id = int(data["id"])
    async with UserService() as service:
        await service.get_or_create_user(
            telegram_id,
            id=telegram_id,
            first_name=data.get("first_name"),
            username=data.get("username"),
            last_name=data.get("last_name"),
            language_code=data.get("language_code"),
        )

    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie("telegram_id", str(telegram_id), max_age=S.SESSION_MAX_AGE, httponly=True)
    return response
