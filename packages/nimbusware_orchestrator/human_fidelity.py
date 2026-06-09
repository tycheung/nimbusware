from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nimbusware_orchestrator.browser_controller import run_ui_flow
from nimbusware_orchestrator.ui_flow_dsl import UiFlowDefinition, UiFlowStep

PERF_BUDGET_MS = 8000


@dataclass
class HumanFidelityResult:
    passed: bool
    checks: list[dict[str, Any]] = field(default_factory=list)
    detail: str = ""


NEGATIVE_LOGIN_FAIL_FLOW = UiFlowDefinition(
    flow_id="negative_login_fail",
    steps=[
        UiFlowStep(kind="goto", url="/"),
        UiFlowStep(kind="fill", selector='input[name="password"]', value="wrong"),
        UiFlowStep(kind="click", selector='button[type="submit"]'),
        UiFlowStep(kind="expect_text", selector="body", value="Invalid"),
    ],
)


def run_axe_smoke(base_url: str) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"ok": False, "detail": "playwright_not_installed"}
    issues: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url.rstrip("/") + "/", wait_until="domcontentloaded")
        title = page.title()
        if page.locator("html[lang]").count() == 0:
            issues.append("missing_lang")
        if page.locator("h1").count() == 0 and not str(title).strip():
            issues.append("missing_heading")
        dcl = page.evaluate(
            """() => {
              const t = performance.timing;
              if (!t || !t.navigationStart) return null;
              return t.domContentLoadedEventEnd - t.navigationStart;
            }""",
        )
        browser.close()
    perf_ok = dcl is None or int(dcl) <= PERF_BUDGET_MS
    if not perf_ok:
        issues.append(f"slow_dcl_{int(dcl)}ms")
    ok = not issues and perf_ok
    detail = "pass" if ok else ",".join(issues) if issues else "perf_budget_exceeded"
    return {"ok": ok, "detail": detail, "title": title, "dcl_ms": dcl}


def run_perf_budget_check(base_url: str) -> dict[str, Any]:
    axe = run_axe_smoke(base_url)
    return {
        "passed": axe.get("ok") is True,
        "detail": str(axe.get("detail") or ""),
        "dcl_ms": axe.get("dcl_ms"),
    }


def _page_has_login_form(base_url: str) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url.rstrip("/") + "/", wait_until="domcontentloaded")
        has_form = page.locator('input[name="password"]').count() > 0
        browser.close()
    return has_form


def run_human_fidelity_suite(base_url: str) -> HumanFidelityResult:
    checks: list[dict[str, Any]] = []
    axe = run_axe_smoke(base_url)
    checks.append({"kind": "a11y_smoke", **axe})
    nav = run_ui_flow(
        base_url,
        UiFlowDefinition(
            flow_id="keyboard_nav",
            steps=[
                UiFlowStep(kind="goto", url="/"),
                UiFlowStep(kind="press", selector="body", value="Tab"),
            ],
        ),
        reuse_context=False,
    )
    checks.append({"kind": "keyboard_nav", "passed": nav.passed, "detail": nav.detail})
    if _page_has_login_form(base_url):
        negative = run_ui_flow(base_url, NEGATIVE_LOGIN_FAIL_FLOW, reuse_context=False)
        checks.append(
            {"kind": "negative_login", "passed": negative.passed, "detail": negative.detail}
        )
    else:
        checks.append({"kind": "negative_login", "passed": True, "detail": "skipped_no_login_form"})
    negative_passed = checks[-1]["passed"] is True
    passed = axe.get("ok") is True and nav.passed and negative_passed
    return HumanFidelityResult(passed=passed, checks=checks, detail="pass" if passed else "fail")
