"""Web application package for FastAPI endpoints."""
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .routes import admin, auth, index, profile, settings

app = FastAPI()
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Redirect unauthenticated users to login and handle dashboard routing."""
    path = request.url.path

    # Allow direct access to API calls using explicit authorization headers
    if request.headers.get("Authorization"):
        return await call_next(request)

    telegram_id = request.cookies.get("telegram_id")

    # Authentication routes
    if path.startswith("/auth"):
        if telegram_id and path == "/auth/login":
            return RedirectResponse("/")
        return await call_next(request)

    # Skip docs and schema endpoints
    if path.startswith("/docs") or path.startswith("/openapi"):
        return await call_next(request)

    # Allow root path for both authenticated and guest users
    if path == "/":
        return await call_next(request)

    # Authenticated users can access other routes directly
    if telegram_id:
        return await call_next(request)

    # For everything else require login, preserving original destination
    next_url = request.url.path
    if request.url.query:
        next_url += "?" + request.url.query
    return RedirectResponse(f"/auth/login?next={quote(next_url, safe='')}")


app.include_router(index.router)
app.include_router(profile.router)
app.include_router(settings.router)
app.include_router(auth.router, prefix="/auth")
app.include_router(admin.router, prefix="/admin")
