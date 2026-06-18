from __future__ import annotations

from pathlib import Path


def playwright_chromium_launchable() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    from nimbusware_orchestrator.playwright_sync import run_without_asyncio_loop

    def _probe() -> bool:
        with sync_playwright() as playwright_api:
            return Path(playwright_api.chromium.executable_path).is_file()

    try:
        return run_without_asyncio_loop(_probe)
    except Exception:
        return False
