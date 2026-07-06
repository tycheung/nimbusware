from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orchestrator.scraper.artifacts import prune_scraper_artifacts
from unit.composite_contracts.matrix_runner import run_exception_matrix, run_value_matrix
from unit.composite_contracts.scraper_artifact_retention_matrix import (
    PRUNE_CLEANUP_CASES,
    PRUNE_MAX_AGE_EXCEPTION_CASES,
    PRUNE_MAX_AGE_VALUE_CASES,
    PRUNE_NESTED_CASES,
    local_removed,
    run_persist_fallback_contract,
    run_prune_case,
)


def _invoke_max_age_exception(case: dict[str, Any], tmp_path: Path) -> None:
    base = tmp_path / case["case_id"]
    prune_scraper_artifacts(base, max_age_days=case["max_age_days"])


def _invoke_max_age_value(case: dict[str, Any], tmp_path: Path) -> int:
    base = tmp_path / case["case_id"]
    return local_removed(base, max_age_days=case["max_age_days"])


@pytest.mark.parametrize("case", PRUNE_MAX_AGE_EXCEPTION_CASES, ids=lambda c: c["case_id"])
def test_prune_max_age_exception_matrix(tmp_path: Path, case: dict[str, Any]) -> None:
    run_exception_matrix((case,), invoke=lambda c: _invoke_max_age_exception(c, tmp_path))


@pytest.mark.parametrize("case", PRUNE_MAX_AGE_VALUE_CASES, ids=lambda c: c["case_id"])
def test_prune_max_age_value_matrix(tmp_path: Path, case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=lambda c: _invoke_max_age_value(c, tmp_path))


@pytest.mark.parametrize("case", PRUNE_NESTED_CASES, ids=lambda c: c["case_id"])
def test_prune_nested_and_cutoff_matrix(tmp_path: Path, case: dict[str, Any]) -> None:
    run_prune_case(tmp_path, case)


@pytest.mark.parametrize("case", PRUNE_CLEANUP_CASES, ids=lambda c: c["case_id"])
def test_prune_cleanup_and_dry_run_matrix(tmp_path: Path, case: dict[str, Any]) -> None:
    run_prune_case(tmp_path, case)


def test_persist_scraper_response_artifact_value_error_fallback_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_persist_fallback_contract(tmp_path, monkeypatch)
