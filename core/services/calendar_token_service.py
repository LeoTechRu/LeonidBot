from __future__ import annotations

from typing import Optional

import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import db
from core.models import CalendarFeedToken


class CalendarTokenService:
    """Manage one-time calendar feed tokens."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.session = session
        self._external = session is not None

    async def __aenter__(self) -> "CalendarTokenService":
        if self.session is None:
            self.session = db.async_session()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover
        if not self._external:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
            await self.session.close()

    async def create_token(self, owner_id: int) -> str:
        """Generate and store a token hash for ``owner_id`` and return raw token."""

        token = secrets.token_urlsafe(16)
        token_hash = db.bcrypt.generate_password_hash(token)
        record = CalendarFeedToken(owner_id=owner_id, token_hash=token_hash)
        self.session.add(record)
        await self.session.flush()
        return token

    async def get_owner_by_token(self, token: str) -> int | None:
        """Return owner_id matching ``token`` or ``None``."""

        stmt = select(CalendarFeedToken)
        res = await self.session.execute(stmt)
        for row in res.scalars():
            if db.bcrypt.check_password_hash(row.token_hash, token):
                return row.owner_id
        return None
