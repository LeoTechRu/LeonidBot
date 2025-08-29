from __future__ import annotations

from typing import Iterable


def can_view(owner_id: int, viewer_id: int, mode: str, members: Iterable[int] | None = None) -> bool:
    """Simple ACL check used in tests.

    - ``single`` mode: viewer must be owner.
    - ``multiplayer`` mode: viewer must be in ``members`` or owner.
    """

    if mode == "single":
        return owner_id == viewer_id
    if mode == "multiplayer":
        members = set(members or []) | {owner_id}
        return viewer_id in members
    return False
