from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from nimbusware_console.workflow_explainers.agent_evaluator import (
    agent_evaluator_workflow_explainer_operator_metrics_table_rows,
)
from unit.workflow_explainer_case_runner import (
    assert_payload_expectations,
    load_explainer_cases_yaml,
    run_and_assert_caption_case,
    run_and_assert_env_payload_case,
    run_and_assert_operator_metrics_case,
    run_explainer_payload_case,
)

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "explainers"
_CASES: dict[str, Any] = load_explainer_cases_yaml(_FIXTURES / "agent_evaluator_cases.yaml")
_SLUG = str(_CASES["slug"])


@pytest.mark.parametrize("case", _CASES.get("payload_cases") or [], ids=lambda c: c["id"])
def test_agent_evaluator_payload_case(case: dict[str, Any], tmp_path: Path) -> None:
    payload = run_explainer_payload_case(_SLUG, case, tmp_path)
    assert_payload_expectations(payload, case)


@pytest.mark.parametrize("case", _CASES.get("caption_cases") or [], ids=lambda c: c["id"])
def test_agent_evaluator_caption_case(case: dict[str, Any]) -> None:
    run_and_assert_caption_case(_SLUG, case)


@pytest.mark.parametrize("case", _CASES.get("caption_repo_cases") or [], ids=lambda c: c["id"])
def test_agent_evaluator_caption_repo_case(case: dict[str, Any], tmp_path: Path) -> None:
    run_and_assert_caption_case(_SLUG, case, tmp_path)


@pytest.mark.parametrize("case", _CASES.get("operator_metrics_cases") or [], ids=lambda c: c["id"])
def test_agent_evaluator_operator_metrics_case(case: dict[str, Any]) -> None:
    run_and_assert_operator_metrics_case(_SLUG, case)


@pytest.mark.parametrize("case", _CASES.get("env_payload_cases") or [], ids=lambda c: c["id"])
def test_agent_evaluator_env_payload_case(
    case: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_and_assert_env_payload_case(_SLUG, case, tmp_path, monkeypatch)


def test_agent_evaluator_workflow_explainer_operator_metrics_load_error() -> None:
    from nimbusware_console.workflow_explainers.agent_evaluator import (
        agent_evaluator_workflow_explainer_operator_metrics,
    )

    m = agent_evaluator_workflow_explainer_operator_metrics({"load_error": "missing file"})
    assert m["load_error_present"] is True
    rows = agent_evaluator_workflow_explainer_operator_metrics_table_rows(m)
    assert any(r["field"] == "Load error" for r in rows)
