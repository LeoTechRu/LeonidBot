"""Common dependencies for FastAPI routes."""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from models import User, UserRole
from services.telegram import UserService


async def get_current_user(request: Request) -> User:
    """Extract the current user from request headers or cookies.

    Supports ``X-Telegram-Id`` and ``Authorization: Bearer <id>`` headers
    and additionally falls back to a ``telegram_id`` cookie set after
    successful login.
    """
    user_id: Optional[int] = None
    cookie_id = request.cookies.get("telegram_id")
    if cookie_id:
        try:
            user_id = int(cookie_id)
        except ValueError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cookie") from exc

    if user_id is None:
        raw = request.headers.get("X-Telegram-Id")
        if raw:
            try:
                user_id = int(raw)
            except ValueError as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid X-Telegram-Id") from exc

    if user_id is None:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
            try:
                user_id = int(token)
            except ValueError as exc:  # pragma: no cover - defensive
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    async with UserService() as service:
        user = await service.get_user_by_telegram_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user


def role_required(required_role: UserRole):
    """Dependency factory ensuring the current user has the given role."""

    async def verifier(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role < required_role.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return verifier
