"""Entry point for the FastAPI application used in tests.

This module exposes a single ``app`` instance that combines the
authentication route defined in :mod:`web.main` with the routers from the
``web.routes`` package.  Historically the project provided ``main.py`` at
repository root; tests and external scripts still import ``main``.  After
refactoring the web application moved under the ``web`` package, so this
file restores the expected import path.
"""
from web import app
from web.routes import profile

# Attach profile router; auth and admin included in web.app
app.include_router(profile.router)
