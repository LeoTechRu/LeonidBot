"""Combined entry point for the Telegram bot and FastAPI web application.

This module keeps the ``app`` object available for tests and external
tools.  When executed as a script it sequentially starts the bot and the
web server.  If one of them fails to launch the error is logged and the
other service still attempts to run.
"""

from __future__ import annotations

import asyncio
import multiprocessing

import uvicorn

from bot.main import main as bot_main
from web import app as fastapi_app
from web.routes import profile
from core.logger import logger

# Expose FastAPI app for tests; attach extra routers
app = fastapi_app
app.include_router(profile.router)


def run_bot() -> None:
    """Start Telegram bot polling."""
    try:
        asyncio.run(bot_main())
    except Exception:  # pragma: no cover - log unexpected errors
        logger.exception("Bot module failed to start")


def run_web() -> None:
    """Run FastAPI application via Uvicorn."""
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception:  # pragma: no cover - log unexpected errors
        logger.exception("Web module failed to start")


def main() -> None:
    """Launch bot then web, allowing the second to start even if first fails."""
    bot_process = multiprocessing.Process(target=run_bot, name="bot")
    bot_process.start()

    web_process = multiprocessing.Process(target=run_web, name="web")
    web_process.start()

    bot_process.join()
    web_process.join()


if __name__ == "__main__":  # pragma: no cover
    main()

