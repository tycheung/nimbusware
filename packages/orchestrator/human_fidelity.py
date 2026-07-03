from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from env.env_flags import env_bool
from orchestrator.browser_controller import run_ui_flow
from orchestrator.playwright_sync import run_without_asyncio_loop
from orchestrator.ui_flow_dsl import UiFlowDefinition, UiFlowStep

PERF_BUDGET_MS = 8000
AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"
AXE_RULE_IDS = ("color-contrast", "document-title", "html-has-lang", "landmark-one-main")


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


def _run_axe_smoke_sync(base_url: str) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

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


def run_axe_smoke(base_url: str) -> dict[str, Any]:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return {"ok": False, "detail": "playwright_not_installed"}
    return run_without_asyncio_loop(lambda: _run_axe_smoke_sync(base_url))


def _run_axe_rules_check_sync(base_url: str) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    violations: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url.rstrip("/") + "/", wait_until="domcontentloaded")
        page.add_script_tag(url=AXE_CDN)
        raw = page.evaluate(
            """async (ruleIds) => {
              if (typeof axe === 'undefined') return { error: 'axe_missing' };
              const results = await axe.run(document, { runOnly: { type: 'rule', values: ruleIds } });
              return {
                violations: (results.violations || []).map((v) => v.id),
              };
            }""",
            list(AXE_RULE_IDS),
        )
        browser.close()
    if isinstance(raw, dict) and raw.get("error"):
        return {"ok": False, "detail": str(raw["error"]), "violations": []}
    if isinstance(raw, dict):
        violations = [str(v) for v in raw.get("violations") or []]
    ok = not violations
    detail = "pass" if ok else ",".join(violations[:6])
    return {"ok": ok, "detail": detail, "violations": violations}


def run_axe_rules_check(base_url: str) -> dict[str, Any]:
    if not env_bool("NIMBUSWARE_AXE_ENABLED", default=False):
        return {"ok": True, "detail": "axe_disabled", "violations": []}
    try:
        import playwright  # noqa: F401
    except ImportError:
        return {"ok": False, "detail": "playwright_not_installed", "violations": []}
    return run_without_asyncio_loop(lambda: _run_axe_rules_check_sync(base_url))


def run_perf_budget_check(base_url: str) -> dict[str, Any]:
    axe = run_axe_smoke(base_url)
    return {
        "passed": axe.get("ok") is True,
        "detail": str(axe.get("detail") or ""),
        "dcl_ms": axe.get("dcl_ms"),
    }


def _page_has_login_form_sync(base_url: str) -> bool:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url.rstrip("/") + "/", wait_until="domcontentloaded")
        has_form = page.locator('input[name="password"]').count() > 0
        browser.close()
    return bool(has_form)


def _page_has_login_form(base_url: str) -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    return run_without_asyncio_loop(lambda: _page_has_login_form_sync(base_url))


def _run_mouse_smoke_sync(base_url: str) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url.rstrip("/") + "/", wait_until="domcontentloaded")
        page.mouse.move(40, 40)
        page.mouse.wheel(0, 240)
        hovered = page.locator("a, button").first
        if hovered.count() > 0:
            hovered.hover(timeout=2000)
        browser.close()
    return {"ok": True, "detail": "mouse_wheel_hover_ok"}


def run_mouse_smoke(base_url: str) -> dict[str, Any]:
    if not env_bool("NIMBUSWARE_MOUSE_FIDELITY", default=False):
        return {"ok": True, "detail": "mouse_disabled"}
    try:
        import playwright  # noqa: F401
    except ImportError:
        return {"ok": False, "detail": "playwright_not_installed"}
    return run_without_asyncio_loop(lambda: _run_mouse_smoke_sync(base_url))


def _run_human_fidelity_suite_sync(base_url: str) -> HumanFidelityResult:
    checks: list[dict[str, Any]] = []
    axe = run_axe_smoke(base_url)
    checks.append({"kind": "a11y_smoke", **axe})
    rules = run_axe_rules_check(base_url)
    checks.append({"kind": "axe_rules", **rules})
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
    mouse = run_mouse_smoke(base_url)
    checks.append(
        {
            "kind": "mouse_smoke",
            "passed": mouse.get("ok") is True,
            "detail": str(mouse.get("detail") or ""),
        },
    )
    if _page_has_login_form(base_url):
        negative = run_ui_flow(base_url, NEGATIVE_LOGIN_FAIL_FLOW, reuse_context=False)
        checks.append(
            {"kind": "negative_login", "passed": negative.passed, "detail": negative.detail}
        )
    else:
        checks.append({"kind": "negative_login", "passed": True, "detail": "skipped_no_login_form"})
    negative_passed = checks[-1]["passed"] is True
    mouse_passed = checks[-2]["passed"] is True
    axe_ok = axe.get("ok") is True and rules.get("ok") is not False
    passed = axe_ok and nav.passed and mouse_passed and negative_passed
    return HumanFidelityResult(passed=passed, checks=checks, detail="pass" if passed else "fail")


def run_human_fidelity_suite(base_url: str) -> HumanFidelityResult:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return HumanFidelityResult(passed=False, detail="playwright_not_installed")
    return run_without_asyncio_loop(lambda: _run_human_fidelity_suite_sync(base_url))
