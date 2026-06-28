from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx

_API_PATHS = ("/health", "/docs", "/openapi.json", "/")
_WEB_PATHS = ("/",)


def _probe_url(
    url: str,
    paths: tuple[str, ...],
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    base = url.rstrip("/") + "/"
    last_error = ""
    for path in paths:
        target = urljoin(base, path.lstrip("/"))
        try:
            resp = httpx.get(target, timeout=timeout_seconds, follow_redirects=True)
            if resp.status_code < 400:
                return {
                    "status": "passed",
                    "detail": f"HTTP {resp.status_code} at {target}",
                    "url": target,
                }
            last_error = f"HTTP {resp.status_code} at {target}"
        except httpx.HTTPError as exc:
            last_error = str(exc)
    return {"status": "failed", "detail": last_error or "request failed", "url": base}


def _playwright_probe(
    web_url: str,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "kind": "playwright",
            "status": "skipped",
            "detail": "playwright not installed",
        }
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(web_url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            title = page.title()
            browser.close()
        if title:
            return {
                "kind": "playwright",
                "status": "passed",
                "detail": f"loaded page title: {title[:80]}",
                "url": web_url,
            }
        return {
            "kind": "playwright",
            "status": "failed",
            "detail": "empty page title",
            "url": web_url,
        }
    except Exception as exc:
        return {
            "kind": "playwright",
            "status": "failed",
            "detail": str(exc)[:300],
            "url": web_url,
        }


def run_deploy_smoke(
    *,
    api_url: str | None = None,
    web_url: str | None = None,
    use_playwright: bool = False,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    targets: list[tuple[str, str, tuple[str, ...]]] = []
    if api_url:
        targets.append(("api", api_url.strip(), _API_PATHS))
    if web_url:
        targets.append(("web", web_url.strip(), _WEB_PATHS))
    if not targets:
        return {
            "status": "skipped",
            "detail": "No live URLs to smoke test",
            "checks": checks,
        }

    ok = True
    for kind, url, paths in targets:
        result = _probe_url(url, paths, timeout_seconds=timeout_seconds)
        result["kind"] = kind
        checks.append(result)
        if result["status"] != "passed":
            ok = False

    if use_playwright and web_url and ok:
        pw = _playwright_probe(web_url.strip(), timeout_seconds=timeout_seconds)
        checks.append(pw)
        if pw["status"] == "failed":
            ok = False

    passed = [c for c in checks if c.get("status") == "passed"]
    detail = f"{len(passed)}/{len(checks)} checks passed"
    return {
        "status": "passed" if ok else "failed",
        "detail": detail,
        "checks": checks,
        "api_url": api_url or "",
        "web_url": web_url or "",
    }
