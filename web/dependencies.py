from fastapi import Depends, HTTPException, Request, status

from core.models import User, UserRole
from core.services.telegram import UserService


async def get_current_user(request: Request) -> User:
    """Получение текущего пользователя по заголовку X-Telegram-Id."""
    telegram_id = request.headers.get("X-Telegram-Id")
    if telegram_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    async with UserService() as service:
        user = await service.get_user_by_telegram_id(int(telegram_id))
    if not user:
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

