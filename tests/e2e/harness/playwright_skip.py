from __future__ import annotations

import pytest


def require_playwright_chromium(*, fail_message: str | None = None) -> None:
    """Skip (or fail) when the Playwright Python package or Chromium binary is unavailable."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        pytest.skip("playwright not installed")

    from nimbusware_orchestrator.playwright_probe import playwright_chromium_launchable

    if not playwright_chromium_launchable():
        if fail_message:
            pytest.fail(fail_message)
        pytest.skip("playwright chromium browser not installed")
