from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from unit.composite_repo_fixtures import write_workflow_profile
from unit.workflow_explainer_case_runner import (
    assert_explainer_export_contract,
    assert_operator_metrics_export_contract,
    load_explainer_export_fns,
)
from unit.workflow_explainer_helpers import (
    build_self_refinement_repo,
    build_universal_critique_stub_repo,
    explainer_payload_for_slug,
)

_FIXTURES = (
    Path(__file__).resolve().parents[1] / "fixtures" / "explainers" / "export_smoke_cases.yaml"
)
_CASES: list[dict[str, Any]] = yaml.safe_load(_FIXTURES.read_text(encoding="utf-8"))["cases"]


def _repo_root_for_case(tmp_path: Path, repo: dict[str, Any]) -> Path:
    fixture = repo.get("fixture")
    if fixture == "universal_critique_stub":
        return build_universal_critique_stub_repo(tmp_path)
    if fixture == "self_refinement_on":
        return build_self_refinement_repo(tmp_path)
    yaml_body = repo.get("workflow_yaml", "version: 1\n")
    write_workflow_profile(tmp_path, str(repo.get("profile", "wf")), yaml_body)
    return tmp_path


@pytest.mark.parametrize("case", _CASES, ids=[c["slug"] for c in _CASES])
def test_workflow_explainer_minimal_export_contract(case: dict[str, Any]) -> None:
    fns = load_explainer_export_fns(case["slug"])
    assert_explainer_export_contract(
        fns,
        case["minimal_payload"],
        export_slug=case["export_slug"],
        required_fields=tuple(case.get("required_fields") or ()),
    )


@pytest.mark.parametrize("case", _CASES, ids=[c["slug"] for c in _CASES])
def test_workflow_explainer_repo_export_contract(
    case: dict[str, Any],
    tmp_path: Path,
) -> None:
    repo = case.get("repo")
    if not repo:
        pytest.skip("no repo fixture")
    root = _repo_root_for_case(tmp_path, repo)
    payload = explainer_payload_for_slug(
        root,
        case["slug"],
        str(repo.get("profile", "wf")),
    )
    fns = load_explainer_export_fns(case["slug"])
    assert_explainer_export_contract(
        fns,
        payload,
        export_slug=case["export_slug"],
        required_fields=tuple(case.get("required_fields") or ()),
    )


@pytest.mark.parametrize("case", _CASES, ids=[c["slug"] for c in _CASES])
def test_workflow_explainer_operator_metrics_export_contract(case: dict[str, Any]) -> None:
    fns = load_explainer_export_fns(case["slug"])
    first_row = case.get("operator_metrics_first_row")
    assert_operator_metrics_export_contract(
        fns,
        first_row_field=first_row if first_row else None,
    )
