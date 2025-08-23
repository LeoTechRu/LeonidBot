from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.templating import Jinja2Templates

from core.models import User, UserRole
from core.services.telegram import UserService

router = APIRouter(prefix="/profile", tags=["profile"])

# Configure templates relative to this file
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


async def get_current_user(request: Request) -> User:
    """Simple dependency to extract current user from session or Authorization header."""
    # Try to read from session if middleware is available
    user_id: Optional[int] = None
    if "session" in request.scope:
        user_id = request.session.get("user_id")

    # Fallback to Authorization header (JWT/Bearer token)
    if user_id is None:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
            try:
                user_id = int(token)
            except ValueError as exc:  # invalid token format
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    async with UserService() as user_service:
        user = await user_service.get_user_by_telegram_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user


@router.get("/{telegram_id}")
async def get_profile(
    request: Request,
    telegram_id: int,
    current_user: User = Depends(get_current_user),
):
    """Render profile for a given telegram id."""
    if telegram_id != current_user.telegram_id and current_user.role <= UserRole.single.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    async with UserService() as user_service:
        user = await user_service.get_user_by_telegram_id(telegram_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return templates.TemplateResponse(request, "profile.html", {"user": user})


@router.post("/{telegram_id}")
async def update_profile(
    request: Request,
    telegram_id: int,
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """Update user profile with role-based access control."""
    if telegram_id != current_user.telegram_id and current_user.role < UserRole.moderator.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    async with UserService() as user_service:
        user = await user_service.update_user(telegram_id, **data)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return templates.TemplateResponse(request, "profile.html", {"user": user})
