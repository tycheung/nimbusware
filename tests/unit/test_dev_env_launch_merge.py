from __future__ import annotations

from agent_core.models import EventType
from nimbusware_orchestrator.dev_env_launch_merge import dev_env_live_regression_from_rows
from nimbusware_orchestrator.launch_evaluator import (
    LaunchEvalScorecard,
    merge_dev_env_into_scorecard,
)


def test_dev_env_live_regression_from_rows() -> None:
    rows = [
        {
            "event_type": EventType.STAGE_PASSED.value,
            "payload": {"stage_name": "dev_env.regression.passed"},
            "metadata": {"dev_env": {"regression": "ok"}},
        },
        {
            "event_type": EventType.STAGE_PASSED.value,
            "payload": {"stage_name": "dev_env.ui_regression.failed"},
            "metadata": {
                "dev_env": {
                    "ui_regression": "button missing",
                    "flow_id": "todo_api_ui",
                    "failed_step": 2,
                    "locator": "testid=todo-add-button",
                }
            },
        },
    ]
    bits = dev_env_live_regression_from_rows(rows)
    assert bits["dev_env_http_regression_passed"] is True
    assert bits["dev_env_ui_regression_passed"] is False
    assert bits["put_ui_flow_id"] == "todo_api_ui"
    assert bits["dev_env_ui_failed_step"] == 2
    assert bits["dev_env_live_regression_passed"] is False


def test_merge_dev_env_into_scorecard() -> None:
    base = LaunchEvalScorecard(
        aggregate=4.5,
        maturity=4.0,
        maintainability=4.0,
        scalability=4.0,
        security=4.0,
        testability=4.0,
        findings=(),
        passed=True,
    )
    rows = [
        {
            "event_type": EventType.STAGE_PASSED.value,
            "payload": {"stage_name": "dev_env.ui_regression.failed"},
            "metadata": {"dev_env": {"regression": "fail"}},
        },
    ]
    merged = merge_dev_env_into_scorecard(base, rows)
    assert merged.passed is False
    assert merged.dev_env_ui_regression_passed is False
    assert any("UI regression" in f for f in merged.findings)
