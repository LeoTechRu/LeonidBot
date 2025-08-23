"""Web application package for FastAPI endpoints."""
from fastapi import FastAPI

from .routes import admin, profile

app = FastAPI()
# Подключаем оба роутера: профиль и админку
app.include_router(profile.router)
app.include_router(admin.router, prefix="/admin")
