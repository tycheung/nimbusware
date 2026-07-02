from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def build_cached_store(
    database_url: str | None,
    *,
    cache: list[T | None],
    memory_factory: Callable[[], T],
    postgres_factory: Callable[[str], T],
) -> T:
    if database_url:
        return postgres_factory(database_url)
    if cache[0] is None:
        cache[0] = memory_factory()
    return cache[0]
