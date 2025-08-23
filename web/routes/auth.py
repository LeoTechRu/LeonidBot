from __future__ import annotations
import hmac, hashlib, time, os
from typing import Dict, List
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from web.config import S
from core.services.telegram import UserService
from core.models import UserRole

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
async def login_page() -> HTMLResponse:
    """Render login page with Telegram widget."""
    bot_user = S.TELEGRAM_BOT_USERNAME
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Вход</title>
</head>
<body>
  <h1>Вход через Telegram</h1>
  <script src=\"https://telegram.org/js/telegram-widget.js?22\"
          data-telegram-login=\"{bot_user}\"
          data-size=\"medium\"
          data-userpic=\"false\"
          data-request-access=\"write\"
          data-lang=\"ru\"
          data-onauth=\"onTelegramAuth(user)\"></script>
  <script>
  async function onTelegramAuth(user) {{
    const form = new URLSearchParams();
    for (const [k, v] of Object.entries(user)) {{ form.append(k, v); }}
    const resp = await fetch('/auth/callback', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/x-www-form-urlencoded' }},
      body: form.toString()
    }});
    if (resp.redirected) {{
      window.location = resp.url;
    }} else {{
      let detail = 'Ошибка авторизации';
      try {{
        const j = await resp.json();
        if (j && j.detail) detail = j.detail;
      }} catch (_) {{}}
      alert(detail);
    }}
  }}
  </script>
</body>
</html>
"""
    return HTMLResponse(html)

@router.post("/callback")
async def telegram_callback(request: Request):
    data = dict((await request.form()).items())
    if not verify_telegram_login(data):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad Telegram signature")
    telegram_id = int(data["id"])  # type: ignore[index]
    admins_raw = os.getenv("ADMIN_TELEGRAM_IDS") or getattr(S, "ADMIN_IDS", "") or ""
    admin_ids: List[int] = []
    for chunk in admins_raw.split(","):
        chunk = chunk.strip()
        if chunk:
            try:
                admin_ids.append(int(chunk))
            except ValueError:
                continue
    role = UserRole.admin if telegram_id in admin_ids else UserRole.single

    async with UserService() as service:
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

    response = RedirectResponse("/admin/users", status_code=303)
    response.set_cookie("telegram_id", str(telegram_id))
    return response
