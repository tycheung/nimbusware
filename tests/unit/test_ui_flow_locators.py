from __future__ import annotations

from unittest.mock import MagicMock

from orchestrator.browser_controller import _execute_step, _locator_to_playwright
from orchestrator.ui_flow_dsl import UiFlowStep, UiLocator


def test_locator_to_playwright_role() -> None:
    page = MagicMock()
    loc = UiLocator(strategy="role", role="button", name="Add")
    _locator_to_playwright(page, loc)
    page.get_by_role.assert_called_once_with("button", name="Add")


def test_locator_to_playwright_testid() -> None:
    page = MagicMock()
    loc = UiLocator(strategy="testid", value="todo-add-button")
    _locator_to_playwright(page, loc)
    page.get_by_test_id.assert_called_once_with("todo-add-button")


def test_execute_step_css_backward_compat() -> None:
    page = MagicMock()
    page.locator.return_value.is_visible.return_value = True
    step = UiFlowStep(kind="expect_visible", selector="form")
    ok, detail = _execute_step(page, "http://127.0.0.1:1", step)
    assert ok is True
    page.locator.assert_called_with("form")


def test_ui_flow_step_from_dict_locator() -> None:
    step = UiFlowStep.from_dict(
        {
            "kind": "click",
            "locator": {"strategy": "role", "role": "link", "name": "Contact"},
        },
    )
    assert step.effective_locator().strategy == "role"
