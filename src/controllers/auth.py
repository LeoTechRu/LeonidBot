from datetime import datetime, timedelta
import hashlib
import hmac
import jwt
from fastapi import APIRouter, HTTPException

from src.config.settings import BOT_TOKEN
from services.telegram import UserService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/telegram")
async def telegram_login(data: dict):
    """Authenticate user via Telegram login widget."""
    received_hash = data.get("hash")
    if not received_hash:
        raise HTTPException(status_code=400, detail="hash required")

    data_check = {k: v for k, v in data.items() if k != "hash"}
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data_check.items())
    )
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if calculated_hash != received_hash:
        raise HTTPException(status_code=403, detail="invalid hash")

    telegram_id = int(data_check["id"])
    async with UserService() as service:
        user_data = {k: v for k, v in data_check.items() if k != "id"}
        await service.get_or_create_user(telegram_id, **user_data)

    payload = {
        "telegram_id": telegram_id,
        "exp": datetime.utcnow() + timedelta(days=1),
    }
    token = jwt.encode(payload, BOT_TOKEN, algorithm="HS256")
    return {"token": token}
