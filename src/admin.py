from __future__ import annotations

import os
from fastapi import FastAPI
from sqlalchemy import select
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend

from db import async_session, engine
from models import Group, LogSettings, User, UserRole


ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change-me")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")


class AdminAuth(AuthenticationBackend):
    """Simple authentication backend using a shared password.

    Access is granted only if the user exists in the database and their
    ``role`` is greater than or equal to ``UserRole.admin``. The login form
    expects the user's Telegram ID as the username and a password defined via
    the ``ADMIN_PASSWORD`` environment variable.
    """

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if password != ADMIN_PASSWORD:
            return False

        if not username:
            return False

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == int(username))
            )
            user: User | None = result.scalars().first()

        if not user or user.role < UserRole.admin.value:
            return False

        request.session.update({"user": user.telegram_id})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool | RedirectResponse:
        if request.session.get("user"):
            return True
        return RedirectResponse("/admin/login")


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.telegram_id, User.username, User.role]


class GroupAdmin(ModelView, model=Group):
    column_list = [Group.id, Group.telegram_id, Group.title, Group.type]


class LogSettingsAdmin(ModelView, model=LogSettings):
    column_list = [LogSettings.id, LogSettings.chat_id, LogSettings.level]


def setup_admin(app: FastAPI) -> Admin:
    """Register admin panel with the FastAPI application."""
    authentication = AdminAuth(secret_key=ADMIN_SECRET)
    admin = Admin(app, engine, authentication_backend=authentication)
    admin.add_view(UserAdmin)
    admin.add_view(GroupAdmin)
    admin.add_view(LogSettingsAdmin)
    return admin
