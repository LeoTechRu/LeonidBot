from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from src.config.settings import BOT_TOKEN
from services.telegram import UserService
import hashlib
import hmac
import time
import jwt

router = APIRouter(tags=["Auth"])


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    """Страница с Telegram Login Widget"""
    auth_url = request.url_for("auth_telegram")
    return f"""
    <html>
      <body>
        <script async src="https://telegram.org/js/telegram-widget.js?22"
                data-telegram-login="{BOT_TOKEN}"
                data-size="large"
                data-auth-url="{auth_url}">
        </script>
      </body>
    </html>
    """


@router.get("/auth/telegram")
async def auth_telegram(request: Request):
    params = dict(request.query_params)
    received_hash = params.pop("hash", None)
    if received_hash is None:
        raise HTTPException(status_code=400, detail="Missing hash")

    auth_date = int(params.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        raise HTTPException(status_code=403, detail="Auth date expired")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if calculated_hash != received_hash:
        raise HTTPException(status_code=403, detail="Invalid hash")

    telegram_id = int(params["id"])
    async with UserService() as user_service:
        user, created = await user_service.get_or_create_user(
            telegram_id=telegram_id,
            first_name=params.get("first_name"),
            last_name=params.get("last_name"),
            username=params.get("username"),
        )
        if not created:
            user.first_name = params.get("first_name", user.first_name)
            user.last_name = params.get("last_name", user.last_name)
            user.username = params.get("username", user.username)
            await user_service.session.flush()

    token = jwt.encode({"telegram_id": telegram_id}, BOT_TOKEN, algorithm="HS256")
    return {"token": token}
