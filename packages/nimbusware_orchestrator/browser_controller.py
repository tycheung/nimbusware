"""Persistent Playwright browser controller for UI regression."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_orchestrator.dev_env_events import emit_dev_env_ui_regression
from nimbusware_orchestrator.ui_flow_dsl import UiFlowDefinition, UiFlowStep

_PERSISTENT: dict[str, Any] = {}


@dataclass
class UiFlowRunResult:
    passed: bool
    steps_run: int = 0
    detail: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)


def _resolve_url(base_url: str, step: UiFlowStep) -> str:
    path = step.url or "/"
    return f"{base_url.rstrip('/')}{path if path.startswith('/') else '/' + path}"


def _execute_step(page: Any, base_url: str, step: UiFlowStep) -> tuple[bool, str]:
    timeout = step.timeout_ms
    if step.kind == "goto":
        page.goto(_resolve_url(base_url, step), wait_until="domcontentloaded", timeout=timeout)
        return True, "goto_ok"
    if step.kind == "click":
        page.locator(step.selector or "body").click(timeout=timeout)
        return True, "click_ok"
    if step.kind == "fill":
        page.locator(step.selector or "input").fill(step.value or "", timeout=timeout)
        return True, "fill_ok"
    if step.kind == "press":
        page.locator(step.selector or "body").press(step.value or "Enter", timeout=timeout)
        return True, "press_ok"
    if step.kind == "select":
        page.locator(step.selector or "select").select_option(step.value or "", timeout=timeout)
        return True, "select_ok"
    if step.kind == "wait_for":
        page.locator(step.selector or "body").wait_for(state="visible", timeout=timeout)
        return True, "wait_ok"
    if step.kind == "expect_text":
        text = page.locator(step.selector or "body").inner_text(timeout=timeout)
        if step.value and step.value not in text:
            return False, f"text_missing:{step.value}"
        return True, "expect_text_ok"
    if step.kind == "expect_visible":
        if not page.locator(step.selector or "body").is_visible(timeout=timeout):
            return False, f"not_visible:{step.selector}"
        return True, "expect_visible_ok"
    return False, f"unknown_step:{step.kind}"


def run_ui_flow(
    base_url: str,
    flow: UiFlowDefinition,
    *,
    workspace_key: str | None = None,
    reuse_context: bool = True,
) -> UiFlowRunResult:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return UiFlowRunResult(passed=False, detail="playwright_not_installed")

    findings: list[dict[str, Any]] = []
    steps_run = 0
    key = workspace_key or base_url

    with sync_playwright() as playwright:
        if reuse_context and key in _PERSISTENT:
            bundle = _PERSISTENT[key]
            page = bundle["page"]
        else:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            _PERSISTENT[key] = {"browser": browser, "context": context, "page": page}

        for step in flow.steps:
            ok, detail = _execute_step(page, base_url, step)
            steps_run += 1
            if not ok:
                findings.append({"step": step.kind, "detail": detail})
                return UiFlowRunResult(
                    passed=False,
                    steps_run=steps_run,
                    detail=detail,
                    findings=findings,
                )
    return UiFlowRunResult(passed=True, steps_run=steps_run, detail="pass", findings=findings)


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
        )
    return result


def close_persistent_browser(workspace: Path) -> None:
    key = str(workspace.resolve())
    bundle = _PERSISTENT.pop(key, None)
    if not bundle:
        return
    for obj in ("context", "browser"):
        try:
            bundle[obj].close()
        except Exception:
            pass
