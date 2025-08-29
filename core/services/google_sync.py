from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


class GoogleCalendarGone(Exception):
    """Raised when sync token is invalid (HTTP 410 GONE)."""


@dataclass
class FakeGoogleCalendar:
    """Minimal in-memory calendar used for sync tests."""

    events: List[str] = field(default_factory=list)
    sync_token: str | None = None
    last_index: int = 0

    def initial_sync(self) -> tuple[List[str], str]:
        """Return all events and a new sync token."""
        self.sync_token = "token"
        self.last_index = len(self.events)
        return list(self.events), self.sync_token

    def incremental_sync(self, token: str) -> tuple[List[str], str]:
        """Return new events since ``token`` or raise if token is invalid."""
        if token != self.sync_token:
            raise GoogleCalendarGone()
        delta = self.events[self.last_index :]
        self.last_index = len(self.events)
        return list(delta), token

    def add_event(self, title: str) -> None:
        self.events.append(title)
