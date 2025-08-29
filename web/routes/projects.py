from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel
from uuid import UUID

from core.models import Project, TgUser, WebUser
from core.services.para_service import ParaService
from core.services.project_notification_service import add_project_notification
from web.dependencies import get_current_tg_user, get_current_web_user
from ..template_env import templates


router = APIRouter(tags=["projects"])
ui_router = APIRouter(prefix="/projects", tags=["projects"], include_in_schema=False)


class ProjectCreate(BaseModel):
    name: str
    area_id: int
    description: Optional[str] = None
    slug: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    area_id: int
    description: Optional[str]
    slug: Optional[str]

    @classmethod
    def from_model(cls, p: Project) -> "ProjectResponse":
        return cls(id=p.id, name=p.name, area_id=p.area_id, description=p.description, slug=p.slug)


class ChannelPayload(BaseModel):
    type: str
    address: Dict[str, Any]


class ProjectNotificationIn(BaseModel):
    channel: ChannelPayload
    rules: Dict[str, Any]


@router.get("", response_model=List[ProjectResponse])
async def list_projects(current_user: TgUser | None = Depends(get_current_tg_user), area_id: int | None = Query(default=None), include_sub: int | None = Query(default=0)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    async with ParaService() as svc:
        if area_id is not None:
            items = await svc.list_projects_by_area(owner_id=current_user.telegram_id, area_id=area_id, include_sub=bool(include_sub))
        else:
            items = await svc.list_projects(owner_id=current_user.telegram_id)
    return [ProjectResponse.from_model(p) for p in items]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, current_user: TgUser | None = Depends(get_current_tg_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    async with ParaService() as svc:
        try:
            p = await svc.create_project(
                owner_id=current_user.telegram_id,
                name=payload.name,
                area_id=payload.area_id,
                slug=payload.slug,
                description=payload.description,
            )
        except PermissionError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return ProjectResponse.from_model(p)


@router.post("/{project_id}/notifications", status_code=status.HTTP_201_CREATED)
async def create_project_notification(
    project_id: UUID,
    payload: ProjectNotificationIn,
    current_user: TgUser | None = Depends(get_current_tg_user),
):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    await add_project_notification(project_id, payload.channel.dict(), payload.rules)
    return {"ok": True}


@ui_router.get("")
async def projects_page(request: Request, current_user: WebUser | None = Depends(get_current_web_user)):
    context = {
        "current_user": current_user,
        "current_role_name": getattr(current_user, "role", ""),
        "is_admin": getattr(current_user, "role", "") == "admin",
        "page_title": "Projects",
    }
    return templates.TemplateResponse(request, "projects.html", context)


# Alias for centralized API mounting
api = router

