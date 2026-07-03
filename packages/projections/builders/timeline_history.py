from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def timeline_history_tail(entries: list[T], *, limit: int = 25) -> list[T]:
    if not entries:
        return []
    if len(entries) <= limit:
        return entries
    return entries[-limit:]


__all__ = ["timeline_history_tail"]
