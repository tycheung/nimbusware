from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_ON_PLAYWRIGHT_THREAD = threading.local()


def _run_on_playwright_thread(fn: Callable[[], T]) -> T:
    import asyncio

    asyncio.set_event_loop(asyncio.new_event_loop())
    _ON_PLAYWRIGHT_THREAD.active = True
    try:
        return fn()
    finally:
        _ON_PLAYWRIGHT_THREAD.active = False


def run_without_asyncio_loop(fn: Callable[[], T]) -> T:
    if getattr(_ON_PLAYWRIGHT_THREAD, "active", False):
        return fn()

    result: list[T] = []
    errors: list[BaseException] = []

    def _target() -> None:
        try:
            result.append(_run_on_playwright_thread(fn))
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(
        target=_target,
        name="nimbusware-playwright-sync",
        daemon=True,
    )
    thread.start()
    thread.join()
    if errors:
        raise errors[0]
    return result[0]
