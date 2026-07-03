from __future__ import annotations

import concurrent.futures
import threading
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

_EXECUTOR: concurrent.futures.ThreadPoolExecutor | None = None
_ON_PLAYWRIGHT_THREAD = threading.local()


def _playwright_executor() -> concurrent.futures.ThreadPoolExecutor:
    global _EXECUTOR
    if _EXECUTOR is None:
        _EXECUTOR = concurrent.futures.ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="nimbusware-playwright-sync",
        )
    return _EXECUTOR


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
    return _playwright_executor().submit(_run_on_playwright_thread, fn).result()
