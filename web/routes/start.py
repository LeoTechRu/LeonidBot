from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.future import select

from core.models import Group, User, UserGroup
from core.services.telegram import UserService
from ..dependencies import get_current_user

templates = Jinja2Templates(directory="web/templates")
router = APIRouter()


@router.get("/start", response_class=HTMLResponse)
async def start_dashboard(request: Request, current_user: User = Depends(get_current_user)):
    async with UserService() as service:
        result = await service.session.execute(
            select(Group).join(UserGroup, Group.telegram_id == UserGroup.group_id).where(
                UserGroup.user_id == current_user.telegram_id
            )
        )
        groups = result.scalars().all()
    return templates.TemplateResponse(
        "start.html", {"request": request, "user": current_user, "groups": groups}
    )
