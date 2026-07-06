from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orchestrator.integrator.gate import (
    load_integrator_gate_emit_enabled,
    load_integrator_min_score_from_thresholds,
    parse_integrator_gate_min_score_to_pass,
)
from unit.composite_contracts.integrator_gate_emit_matrix import (
    INTEGRATOR_GATE_EMIT_BOOL_LADDER_CASES,
    INTEGRATOR_GATE_EMIT_DEFENSIVE_CASES,
)
from unit.composite_contracts.integrator_thresholds_loader_matrix import (
    CROSS_FUNCTION_D1,
    CROSS_FUNCTION_D2_STAGES,
    CROSS_FUNCTION_D4,
    CROSS_FUNCTION_D5_CASES,
    MIN_SCORE_DEFENSIVE_CASES,
    MIN_SCORE_HAPPY_CASES,
    MIN_SCORE_TYPE_ERROR_CASES,
    MIN_SCORE_VALUE_ERROR_CASES,
    NO_CLAMP_CASES,
)
from unit.composite_contracts.matrix_runner import run_exception_matrix, run_value_matrix
from unit.composite_repo_fixtures import (
    write_integrator_thresholds,
    write_workflow_integrator_min_score_yaml,
)


def _write_thresholds(repo: Path, yaml_body: str | None) -> None:
    if yaml_body is None:
        return
    write_integrator_thresholds(repo, yaml_body)


def _thresholds_body(case: dict[str, Any]) -> str | None:
    fragment = case.get("yaml_fragment")
    if fragment is not None:
        return f"version: 1\n{fragment}\n"
    return case.get("yaml_body")


def _load_gate_emit(repo: Path, case: dict[str, Any]) -> bool:
    _write_thresholds(repo, case.get("yaml_body"))
    return load_integrator_gate_emit_enabled(repo)


def _load_min_score(repo: Path, case: dict[str, Any]) -> float:
    _write_thresholds(repo, _thresholds_body(case))
    return load_integrator_min_score_from_thresholds(repo)


@pytest.mark.parametrize("case", INTEGRATOR_GATE_EMIT_DEFENSIVE_CASES, ids=lambda c: c["case_id"])
def test_load_integrator_gate_emit_enabled_defensive_matrix(
    tmp_path: Path, case: dict[str, Any]
) -> None:
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    assert _load_gate_emit(repo, case) is case["expected"]


@pytest.mark.parametrize("case", INTEGRATOR_GATE_EMIT_BOOL_LADDER_CASES, ids=lambda c: c["case_id"])
def test_load_integrator_gate_emit_enabled_bool_ladder_matrix(
    tmp_path: Path, case: dict[str, Any]
) -> None:
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    assert _load_gate_emit(repo, case) is case["expected"]


@pytest.mark.parametrize("case", MIN_SCORE_DEFENSIVE_CASES, ids=lambda c: c["case_id"])
def test_load_integrator_min_score_defensive_matrix(tmp_path: Path, case: dict[str, Any]) -> None:
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    run_value_matrix((case,), invoke=lambda c: _load_min_score(repo, c))


@pytest.mark.parametrize("case", MIN_SCORE_TYPE_ERROR_CASES, ids=lambda c: c["case_id"])
def test_load_integrator_min_score_type_error_matrix(tmp_path: Path, case: dict[str, Any]) -> None:
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    run_value_matrix((case,), invoke=lambda c: _load_min_score(repo, c))


@pytest.mark.parametrize("case", MIN_SCORE_VALUE_ERROR_CASES, ids=lambda c: c["case_id"])
def test_load_integrator_min_score_value_error_matrix(tmp_path: Path, case: dict[str, Any]) -> None:
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    run_value_matrix((case,), invoke=lambda c: _load_min_score(repo, c))


@pytest.mark.parametrize("case", MIN_SCORE_HAPPY_CASES, ids=lambda c: c["case_id"])
def test_load_integrator_min_score_happy_matrix(tmp_path: Path, case: dict[str, Any]) -> None:
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    actual = _load_min_score(repo, case)
    assert actual == pytest.approx(case["expected"]), case["case_id"]


def test_cross_function_d1_shared_path_matrix(tmp_path: Path) -> None:
    case = CROSS_FUNCTION_D1
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    write_integrator_thresholds(repo, case["yaml_body"])
    assert load_integrator_gate_emit_enabled(repo) is case["expected_emit"], case["case_id"]
    assert load_integrator_min_score_from_thresholds(repo) == pytest.approx(
        case["expected_min_score"]
    ), case["case_id"]


@pytest.mark.parametrize("stage", CROSS_FUNCTION_D2_STAGES, ids=lambda c: c["case_id"])
def test_cross_function_d2_independent_probes_matrix(tmp_path: Path, stage: dict[str, Any]) -> None:
    repo = tmp_path / stage["case_id"]
    repo.mkdir()
    _write_thresholds(repo, stage.get("yaml_body"))
    assert load_integrator_gate_emit_enabled(repo) is stage["expected_emit"], stage["case_id"]
    assert load_integrator_min_score_from_thresholds(repo) == stage["expected_min_score"], stage[
        "case_id"
    ]


@pytest.mark.parametrize("case", NO_CLAMP_CASES, ids=lambda c: c["case_id"])
def test_cross_function_d3_no_clamp_asymmetry_matrix(tmp_path: Path, case: dict[str, Any]) -> None:
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    write_integrator_thresholds(
        repo,
        f"version: 1\nenabled: true\nmin_score_to_pass: {case['raw']}\n",
    )
    thresholds_value = load_integrator_min_score_from_thresholds(repo)
    assert thresholds_value == pytest.approx(case["expected"]), case["case_id"]
    write_workflow_integrator_min_score_yaml(repo, case["case_id"], case["raw"])
    wf_value = parse_integrator_gate_min_score_to_pass(repo, case["case_id"])
    clamped = max(0.0, min(1.0, case["expected"]))
    assert wf_value == pytest.approx(clamped), case["case_id"]


def test_cross_function_d4_return_types_matrix(tmp_path: Path) -> None:
    case = CROSS_FUNCTION_D4
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    write_integrator_thresholds(repo, case["thresholds_yaml"])
    thresholds_no_key = load_integrator_min_score_from_thresholds(repo)
    assert isinstance(thresholds_no_key, float), case["case_id"]
    assert thresholds_no_key == 0.0, case["case_id"]
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{case['wf_profile']}.yaml").write_text(case["wf_yaml_body"], encoding="utf-8")
    wf_no_key = parse_integrator_gate_min_score_to_pass(repo, case["wf_profile"])
    assert wf_no_key is None, case["case_id"]


@pytest.mark.parametrize("case", CROSS_FUNCTION_D5_CASES, ids=lambda c: c["case_id"])
def test_cross_function_d5_propagate_non_mapping_matrix(
    tmp_path: Path, case: dict[str, Any]
) -> None:
    repo = tmp_path / case["case_id"]
    repo.mkdir()
    write_integrator_thresholds(repo, case["yaml_body"])

    def invoke(c: dict[str, Any]) -> Any:
        if c["loader"] == "emit":
            return load_integrator_gate_emit_enabled(repo)
        return load_integrator_min_score_from_thresholds(repo)

    run_exception_matrix((case,), invoke=invoke)
