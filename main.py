"""Run Telegram bot and FastAPI app with graceful error handling.

This module exposes the FastAPI ``app`` instance for tests while providing a
command line entry point that starts the bot and the web application in
sequence.  If one component fails to start, the other continues running and
the exception is logged.
"""

from __future__ import annotations

import asyncio
import logging

from web import app

logger = logging.getLogger(__name__)


async def _run_bot() -> None:
    """Start the Telegram bot polling loop."""
    try:
        from bot.main import main as bot_main

        await bot_main()
    except Exception:  # pragma: no cover - log and continue running web
        logger.exception("Bot module failed to start")


async def _run_web() -> None:
    """Run the FastAPI application via uvicorn."""
    try:
        import uvicorn

        config = uvicorn.Config(app, host="0.0.0.0", port=5800, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    except Exception:  # pragma: no cover - log and keep bot running
        logger.exception("Web module failed to start")


async def main() -> None:
    """Launch bot then web; log failures for each module separately."""
    tasks = []

    try:
        tasks.append(asyncio.create_task(_run_bot()))
    except Exception:  # pragma: no cover
        logger.exception("Failed to schedule bot task")

    try:
        tasks.append(asyncio.create_task(_run_web()))
    except Exception:  # pragma: no cover
        logger.exception("Failed to schedule web task")

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            if isinstance(res, Exception):  # pragma: no cover
                logger.exception("Service crashed", exc_info=res)


if __name__ == "__main__":
    asyncio.run(main())

