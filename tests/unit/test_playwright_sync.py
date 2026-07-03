from __future__ import annotations

import asyncio

from orchestrator.playwright_sync import run_without_asyncio_loop


def test_run_without_asyncio_loop_inline_without_asyncio() -> None:
    assert run_without_asyncio_loop(lambda: 41) == 41


def test_run_without_asyncio_loop_offloads_under_asyncio() -> None:
    async def _run() -> int:
        return run_without_asyncio_loop(lambda: 42)

    assert asyncio.run(_run()) == 42
