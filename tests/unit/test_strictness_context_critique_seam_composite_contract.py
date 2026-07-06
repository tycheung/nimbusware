from __future__ import annotations

from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from pydantic import ValidationError

from orchestrator._pipeline import base as orchestrator_base
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.workflow.universal_critique import EffectiveUniversalCritique
from unit.composite_contracts.matrix_runner import run_exception_matrix, run_value_matrix
from unit.composite_contracts.strictness_context_critique_matrix import (
    CROSS_HELPER_CASES,
    EUC_SEAM_CASES,
    STRICTNESS_FS_EMPTY_CASES,
    STRICTNESS_FS_EXCEPTION_CASES,
    STRICTNESS_FS_VALUE_CASES,
    STRICTNESS_IDEMPOTENCY_CASE,
    STRICTNESS_REAL_PATH_VALUE_CASES,
    STRICTNESS_SNAPSHOT_WIRING_CASE,
)
from unit.composite_orchestrator_fixtures import all_false_effective_critique
from unit.composite_store_fixtures import inject_raw_run_created_row


def _strictness_context_patched(case: dict[str, Any]) -> dict[str, Any]:
    orch, _ = make_dev_orchestrator()
    rid = uuid4()
    with patch.object(orch, "policy_snapshot_for_run", return_value=case["policy_snapshot"]):
        return orch._strictness_context(rid)  # noqa: SLF001


def _strictness_context_real_path(case: dict[str, Any]) -> dict[str, Any]:
    orch, _ = make_dev_orchestrator()
    setup = case["setup"]
    if setup == "create_run_default":
        rid = orch.create_run("default")
    elif setup == "create_run_overrides":
        rid = orch.create_run("default", run_policy_overrides=case["run_policy_overrides"])
    else:
        rid = uuid4()
    return orch._strictness_context(rid)  # noqa: SLF001


def _fake_euc(captured: dict[str, Any]):
    def _inner(repo_root: Any, wf: Any) -> EffectiveUniversalCritique:
        captured["repo_root"] = repo_root
        captured["wf"] = wf
        return all_false_effective_critique()

    return _inner


def _invoke_euc_seam(case: dict[str, Any]) -> Any:
    orch, mem = make_dev_orchestrator()
    setup = case["setup"]
    captured: dict[str, Any] = {}
    if setup == "create_run_default":
        rid = orch.create_run("default")
    elif setup == "inject_int_profile":
        rid = uuid4()
        inject_raw_run_created_row(mem, rid, workflow_profile=123)
    elif setup == "inject_two_profiles":
        rid = uuid4()
        inject_raw_run_created_row(mem, rid, workflow_profile="first")
        inject_raw_run_created_row(mem, rid, workflow_profile="second")
    elif setup == "no_rows":
        rid = uuid4()
    else:
        raise ValueError(f"unknown euc setup: {setup!r}")
    if case["case_id"] == "c3_real_call":
        return orch._effective_universal_critique_for_run(rid)  # noqa: SLF001
    with patch.object(
        orchestrator_base, "effective_universal_critique", side_effect=_fake_euc(captured)
    ):
        result = orch._effective_universal_critique_for_run(rid)  # noqa: SLF001
    captured["result"] = result
    return captured


def _invoke_cross_helper(case: dict[str, Any]) -> Any:
    setup = case["setup"]
    orch, mem = make_dev_orchestrator()
    if setup == "dual_call":
        rid = orch.create_run("default")
        with patch.object(
            orch._store,  # noqa: SLF001
            "list_run_events",
            wraps=orch._store.list_run_events,  # noqa: SLF001
        ) as mock_lre:
            orch._strictness_context(rid)  # noqa: SLF001
            orch._effective_universal_critique_for_run(rid)  # noqa: SLF001
        case["mock_lre"] = mock_lre
        case["rid"] = rid
        return None
    if setup == "strictness_and_euc":
        rid = orch.create_run(
            "default",
            run_policy_overrides={
                "finding_fix_strictness": {
                    "minimum_severity_requiring_fixes": "HIGH",
                    "also_require_fixes_for_low_severity": True,
                }
            },
        )
        case["ctx"] = orch._strictness_context(rid)  # noqa: SLF001
        captured: dict[str, Any] = {}
        with patch.object(
            orchestrator_base, "effective_universal_critique", side_effect=_fake_euc(captured)
        ):
            orch._effective_universal_critique_for_run(rid)  # noqa: SLF001
        case["captured"] = captured
        return None
    if setup == "dual_call_readonly":
        rid = orch.create_run("default")
        case["rows_before"] = len(mem._rows)  # noqa: SLF001
        orch._strictness_context(rid)  # noqa: SLF001
        orch._effective_universal_critique_for_run(rid)  # noqa: SLF001
        case["rows_after"] = len(mem._rows)  # noqa: SLF001
        return None
    if setup == "euc_no_rows":
        captured = {}
        with patch.object(
            orchestrator_base, "effective_universal_critique", side_effect=_fake_euc(captured)
        ):
            orch._effective_universal_critique_for_run(uuid4())  # noqa: SLF001
        captured["orch_repo_root"] = orch.repo_root
        return captured
    if setup == "bad_strictness_euc_ok":
        rid = orch.create_run("default")
        bad_snap = {"finding_fix_strictness": {"minimum_severity_requiring_fixes": "BOGUS"}}
        with patch.object(orch, "policy_snapshot_for_run", return_value=bad_snap):
            with pytest.raises(ValidationError):
                orch._strictness_context(rid)  # noqa: SLF001
            return orch._effective_universal_critique_for_run(rid)  # noqa: SLF001
    raise ValueError(f"unknown cross_helper setup: {setup!r}")


@pytest.mark.parametrize("case", STRICTNESS_FS_VALUE_CASES, ids=lambda c: c["case_id"])
def test_strictness_context_fs_value_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_strictness_context_patched)


@pytest.mark.parametrize("case", STRICTNESS_FS_EXCEPTION_CASES, ids=lambda c: c["case_id"])
def test_strictness_context_fs_exception_matrix(case: dict[str, Any]) -> None:
    run_exception_matrix((case,), invoke=_strictness_context_patched)


@pytest.mark.parametrize("case", STRICTNESS_FS_EMPTY_CASES, ids=lambda c: c["case_id"])
def test_strictness_context_fs_empty_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_strictness_context_patched)


@pytest.mark.parametrize("case", STRICTNESS_REAL_PATH_VALUE_CASES, ids=lambda c: c["case_id"])
def test_strictness_context_real_path_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_strictness_context_real_path)


def test_strictness_context_snapshot_wiring_matrix() -> None:
    case = STRICTNESS_SNAPSHOT_WIRING_CASE
    orch, _ = make_dev_orchestrator()
    rid = orch.create_run("default")
    case["rid"] = rid
    with patch.object(
        orch,
        "policy_snapshot_for_run",
        wraps=orch.policy_snapshot_for_run,
    ) as mock_snap:
        orch._strictness_context(rid)  # noqa: SLF001
    case["mock_snap"] = mock_snap
    case["validate"](case, None)


def test_strictness_context_idempotency_matrix() -> None:
    case = STRICTNESS_IDEMPOTENCY_CASE
    orch, _ = make_dev_orchestrator()
    rid = orch.create_run("default")
    ctx_first = orch._strictness_context(rid)  # noqa: SLF001
    ctx_second = orch._strictness_context(rid)  # noqa: SLF001
    case["validate"](case, (ctx_first, ctx_second))


@pytest.mark.parametrize("case", EUC_SEAM_CASES, ids=lambda c: c["case_id"])
def test_effective_universal_critique_seam_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_euc_seam)


@pytest.mark.parametrize("case", CROSS_HELPER_CASES, ids=lambda c: c["case_id"])
def test_cross_helper_key_divergences_matrix(case: dict[str, Any]) -> None:
    run_value_matrix((case,), invoke=_invoke_cross_helper)
