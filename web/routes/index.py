"""Root and helper routes for the web application."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.services.telegram import UserService

router = APIRouter()


@router.get("/", include_in_schema=False)
async def index(request: Request) -> RedirectResponse:
    """Redirect authenticated users to the dashboard.

    Unauthenticated visitors are redirected to the login page instead.
    """

    user_id = request.cookies.get("telegram_id")
    if user_id:
        try:
            telegram_id = int(user_id)
        except ValueError:
            telegram_id = None
        if telegram_id is not None:
            async with UserService() as service:
                user = await service.get_user_by_telegram_id(telegram_id)
                if user:
                    return RedirectResponse("/start")

    return RedirectResponse("/auth/login")


@router.get("/admin", include_in_schema=False)
async def admin_index() -> RedirectResponse:
    """Convenience redirect for admin panel."""

    return RedirectResponse("/admin/users")
