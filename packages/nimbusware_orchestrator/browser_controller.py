from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_orchestrator.dev_env_events import emit_dev_env_ui_regression
from nimbusware_orchestrator.playwright_sync import run_without_asyncio_loop
from nimbusware_orchestrator.ui_flow_dsl import UiFlowDefinition, UiFlowStep, UiLocator

_PERSISTENT: dict[str, dict[str, Any]] = {}

_BROWSER_IO_ERRORS = (OSError, RuntimeError, AttributeError, ValueError)


def _page_alive(page: Any) -> bool:
    try:
        page.title()
        return True
    except _BROWSER_IO_ERRORS:
        return False


def _close_bundle_key(key: str) -> None:
    bundle = _PERSISTENT.pop(key, None)
    if not bundle:
        return
    for obj in ("page", "context", "browser"):
        target = bundle.get(obj)
        if target is not None:
            try:
                target.close()
            except _BROWSER_IO_ERRORS:
                pass
    mgr = bundle.get("mgr")
    if mgr is not None:
        try:
            mgr.stop()
        except _BROWSER_IO_ERRORS:
            pass


@dataclass
class UiFlowRunResult:
    passed: bool
    steps_run: int = 0
    detail: str = ""
    flow_id: str = ""
    failed_step: int | None = None
    failed_locator: str | None = None
    findings: list[dict[str, Any]] = field(default_factory=list)


def _resolve_url(base_url: str, step: UiFlowStep) -> str:
    path = step.url or "/"
    return f"{base_url.rstrip('/')}{path if path.startswith('/') else '/' + path}"


def _locator_to_playwright(page: Any, locator: UiLocator) -> Any:
    if locator.strategy == "role":
        return page.get_by_role(locator.role or "button", name=locator.name or "")
    if locator.strategy == "testid":
        return page.get_by_test_id(locator.value or "")
    if locator.strategy == "label":
        return page.get_by_label(locator.value or "")
    if locator.strategy == "text":
        return page.get_by_text(locator.value or "")
    return page.locator(locator.value or "body")


def _locator_label(locator: UiLocator) -> str:
    if locator.strategy == "role":
        return f"role={locator.role}:{locator.name}"
    return f"{locator.strategy}={locator.value}"


def _execute_step(page: Any, base_url: str, step: UiFlowStep) -> tuple[bool, str]:
    timeout = step.timeout_ms
    loc = step.effective_locator()
    if step.kind == "goto":
        page.goto(_resolve_url(base_url, step), wait_until="domcontentloaded", timeout=timeout)
        return True, "goto_ok"
    target = _locator_to_playwright(page, loc)
    if step.kind == "click":
        target.click(timeout=timeout)
        return True, "click_ok"
    if step.kind == "fill":
        target.fill(step.value or "", timeout=timeout)
        return True, "fill_ok"
    if step.kind == "press":
        target.press(step.value or "Enter", timeout=timeout)
        return True, "press_ok"
    if step.kind == "select":
        target.select_option(step.value or "", timeout=timeout)
        return True, "select_ok"
    if step.kind == "wait_for":
        target.wait_for(state="visible", timeout=timeout)
        return True, "wait_ok"
    if step.kind == "expect_text":
        text = target.inner_text(timeout=timeout)
        if step.value and step.value not in text:
            return False, f"text_missing:{step.value}"
        return True, "expect_text_ok"
    if step.kind == "expect_visible":
        if not target.is_visible(timeout=timeout):
            return False, f"not_visible:{_locator_label(loc)}"
        return True, "expect_visible_ok"
    return False, f"unknown_step:{step.kind}"


def _run_ui_flow_sync(
    base_url: str,
    flow: UiFlowDefinition,
    *,
    workspace_key: str | None,
    reuse_context: bool,
) -> UiFlowRunResult:
    from playwright.sync_api import sync_playwright

    findings: list[dict[str, Any]] = []
    steps_run = 0
    key = workspace_key or base_url
    page: Any | None = None
    ephemeral_mgr: Any | None = None
    ephemeral_browser: Any | None = None
    ephemeral_context: Any | None = None

    if reuse_context and key in _PERSISTENT and _page_alive(_PERSISTENT[key]["page"]):
        page = _PERSISTENT[key]["page"]
    elif reuse_context and key in _PERSISTENT:
        _close_bundle_key(key)

    if page is None:
        ephemeral_mgr = sync_playwright().start()
        try:
            ephemeral_browser = ephemeral_mgr.chromium.launch(headless=True)
            ephemeral_context = ephemeral_browser.new_context()
            page = ephemeral_context.new_page()
            if reuse_context:
                _PERSISTENT[key] = {
                    "mgr": ephemeral_mgr,
                    "browser": ephemeral_browser,
                    "context": ephemeral_context,
                    "page": page,
                }
                ephemeral_mgr = ephemeral_browser = ephemeral_context = None
        except Exception:
            if ephemeral_mgr is not None:
                try:
                    ephemeral_mgr.stop()
                except _BROWSER_IO_ERRORS:
                    pass
            raise

    try:
        for step in flow.steps:
            ok, detail = _execute_step(page, base_url, step)
            steps_run += 1
            if not ok:
                loc = step.effective_locator()
                findings.append(
                    {
                        "step": step.kind,
                        "detail": detail,
                        "locator": _locator_label(loc),
                        "step_index": steps_run,
                    },
                )
                return UiFlowRunResult(
                    passed=False,
                    steps_run=steps_run,
                    detail=detail,
                    flow_id=flow.flow_id,
                    failed_step=steps_run,
                    failed_locator=_locator_label(loc),
                    findings=findings,
                )
        return UiFlowRunResult(
            passed=True,
            steps_run=steps_run,
            detail="pass",
            flow_id=flow.flow_id,
            findings=findings,
        )
    finally:
        if ephemeral_mgr is not None:
            for obj in (ephemeral_context, ephemeral_browser):
                if obj is not None:
                    try:
                        obj.close()
                    except _BROWSER_IO_ERRORS:
                        pass
            ephemeral_mgr.stop()


def run_ui_flow(
    base_url: str,
    flow: UiFlowDefinition,
    *,
    workspace_key: str | None = None,
    reuse_context: bool = True,
) -> UiFlowRunResult:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return UiFlowRunResult(
            passed=False, detail="playwright_not_installed", flow_id=flow.flow_id
        )
    return run_without_asyncio_loop(
        lambda: _run_ui_flow_sync(
            base_url,
            flow,
            workspace_key=workspace_key,
            reuse_context=reuse_context,
        )
    )


def run_dev_env_ui_regression(
    store: Any,
    run_id: UUID | str,
    *,
    base_url: str,
    flow: UiFlowDefinition,
    workspace: Path,
    emit_events: bool = True,
) -> UiFlowRunResult:
    result = run_ui_flow(
        base_url,
        flow,
        workspace_key=str(workspace.resolve()),
        reuse_context=True,
    )
    if emit_events:
        emit_dev_env_ui_regression(
            store,
            run_id,
            passed=result.passed,
            steps_run=result.steps_run,
            detail=result.detail,
            flow_id=result.flow_id or flow.flow_id,
            failed_step=result.failed_step,
            locator=result.failed_locator,
        )
    return result


def close_persistent_browser(workspace: Path) -> None:
    run_without_asyncio_loop(lambda: _close_bundle_key(str(workspace.resolve())))


def close_persistent_browser_url(base_url: str) -> None:
    run_without_asyncio_loop(lambda: _close_bundle_key(base_url.rstrip("/")))


def close_all_persistent_browsers() -> None:
    run_without_asyncio_loop(_close_all_persistent_browsers_sync)


def _close_all_persistent_browsers_sync() -> None:
    for key in list(_PERSISTENT):
        _close_bundle_key(key)
