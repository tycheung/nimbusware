from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from nimbusware_env.env_flags import env_str


@dataclass(frozen=True)
class FleetPlaywrightProbe:
    enabled: bool
    connected: bool
    ws_endpoint: str | None = None
    detail: str = ""


def fleet_playwright_ws_endpoint() -> str | None:
    raw = env_str("NIMBUSWARE_FLEET_PLAYWRIGHT_WS_ENDPOINT").strip()
    return raw or None


def fleet_playwright_config() -> dict[str, Any]:
    ws = fleet_playwright_ws_endpoint()
    if not ws:
        return {"enabled": False}
    return {"enabled": True, "ws_endpoint": ws, "mode": "remote_ws"}


def attach_fleet_playwright_capture(capture: dict[str, Any]) -> dict[str, Any]:
    cfg = fleet_playwright_config()
    if cfg.get("enabled"):
        capture["fleet_playwright"] = cfg
        probe = probe_fleet_playwright_endpoint()
        capture["fleet_playwright"]["connected"] = probe.connected
        if probe.detail:
            capture["fleet_playwright"]["detail"] = probe.detail
    return capture


def probe_fleet_playwright_endpoint(*, timeout_seconds: float = 5.0) -> FleetPlaywrightProbe:
    ws = fleet_playwright_ws_endpoint()
    if not ws:
        return FleetPlaywrightProbe(enabled=False, connected=False, detail="fleet endpoint unset")
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return FleetPlaywrightProbe(
            enabled=True,
            connected=False,
            ws_endpoint=ws,
            detail="playwright module not installed",
        )
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect(ws, timeout=timeout_seconds * 1000)
            try:
                version = browser.version
            finally:
                browser.close()
        return FleetPlaywrightProbe(
            enabled=True,
            connected=True,
            ws_endpoint=ws,
            detail=f"connected ({version})",
        )
    except (PlaywrightError, OSError, TimeoutError) as exc:
        return FleetPlaywrightProbe(
            enabled=True,
            connected=False,
            ws_endpoint=ws,
            detail=str(exc)[:500],
        )


@contextmanager
def fleet_playwright_page(
    *,
    timeout_seconds: float = 30.0,
) -> Iterator[Any | None]:
    ws = fleet_playwright_ws_endpoint()
    if not ws:
        yield None
        return
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        yield None
        return
    playwright = sync_playwright().start()
    browser = None
    page = None
    try:
        browser = playwright.chromium.connect(ws, timeout=timeout_seconds * 1000)
        context = browser.new_context()
        page = context.new_page()
        yield page
    except (PlaywrightError, OSError, TimeoutError):
        yield None
    finally:
        if page is not None:
            try:
                page.context.close()
            except Exception:
                pass
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        playwright.stop()


def fleet_browser_goto(base_url: str, path: str = "/") -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path if path.startswith('/') else '/' + path}"
    with fleet_playwright_page() as page:
        if page is None:
            return {"ok": False, "url": url, "detail": "fleet browser unavailable"}
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
            status = response.status if response is not None else None
            return {
                "ok": status is not None and status < 500,
                "url": url,
                "status": status,
                "title": page.title(),
            }
        except Exception as exc:
            return {"ok": False, "url": url, "detail": str(exc)[:500]}
