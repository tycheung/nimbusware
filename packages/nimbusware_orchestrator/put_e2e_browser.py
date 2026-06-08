from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.fleet_playwright import fleet_playwright_ws_endpoint
from nimbusware_orchestrator.put_e2e_runner import PutE2EFinding


def _goto_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path if path.startswith('/') else '/' + path}"


def _severity_for_status(status: int) -> str:
    if status >= 500:
        return "operational"
    if status >= 400:
        return "info"
    return "info"


def _attach_console_listeners(page: Any, *, findings: list[PutE2EFinding]) -> None:
    def on_console(msg: Any) -> None:
        level = str(getattr(msg, "type", "log") or "log")
        text = str(getattr(msg, "text", "") or "")[:500]
        severity = "operational" if level in {"error", "warning"} else "info"
        findings.append(
            PutE2EFinding(kind="console", message=f"[{level}] {text}", severity=severity),
        )

    def on_page_error(exc: Any) -> None:
        findings.append(
            PutE2EFinding(
                kind="console",
                message=f"pageerror: {exc}",
                severity="operational",
            ),
        )

    page.on("console", on_console)
    page.on("pageerror", on_page_error)


def _attach_network_listeners(page: Any, *, findings: list[PutE2EFinding]) -> None:
    def on_response(resp: Any) -> None:
        status = int(getattr(resp, "status", 0) or 0)
        if status < 400:
            return
        url = str(getattr(resp, "url", "") or "")
        findings.append(
            PutE2EFinding(
                kind="network",
                message=f"HTTP {status} {url}",
                surface_path=url,
                severity=_severity_for_status(status),
            ),
        )

    page.on("response", on_response)


def _run_browser_session(
    url: str,
    *,
    evidence_dir: Path,
    capture_console: bool,
    capture_network: bool,
) -> dict[str, Any]:
    trace_path = evidence_dir / "trace.zip"
    findings: list[PutE2EFinding] = []
    ws = fleet_playwright_ws_endpoint()
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "trace_mode": "unavailable",
            "detail": "playwright module not installed",
            "findings": [],
        }

    playwright_error: tuple[type[BaseException], ...] = (PlaywrightError, OSError, TimeoutError)

    def _drive(context: Any, page: Any, *, backend: str) -> dict[str, Any]:
        if capture_console:
            _attach_console_listeners(page, findings=findings)
        if capture_network:
            _attach_network_listeners(page, findings=findings)
        context.tracing.start(screenshots=True, snapshots=True)
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        context.tracing.stop(path=str(trace_path))
        return {
            "trace_mode": "live",
            "trace_path": str(trace_path),
            "trace_backend": backend,
            "url": url,
            "findings": [f.to_dict() for f in findings],
        }

    try:
        if ws:
            playwright = sync_playwright().start()
            browser = None
            try:
                browser = playwright.chromium.connect(ws, timeout=30000)
                context = browser.new_context()
                page = context.new_page()
                result = _drive(context, page, backend="fleet")
                context.close()
                return result
            finally:
                if browser is not None:
                    try:
                        browser.close()
                    except Exception:
                        pass
                playwright.stop()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            result = _drive(context, page, backend="local")
            browser.close()
            return result
    except playwright_error as exc:
        return {
            "trace_mode": "error",
            "detail": str(exc)[:500],
            "url": url,
            "findings": [f.to_dict() for f in findings],
        }


def capture_failure_browser_trace(
    base_url: str,
    path: str,
    *,
    evidence_dir: Path,
    capture_console: bool = False,
    capture_network: bool = False,
) -> dict[str, Any]:
    """Best-effort Playwright trace and optional console/network capture on failure."""
    return _run_browser_session(
        _goto_url(base_url, path),
        evidence_dir=evidence_dir,
        capture_console=capture_console,
        capture_network=capture_network,
    )
