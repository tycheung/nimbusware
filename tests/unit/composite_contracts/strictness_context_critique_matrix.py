from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from agent_core.models.events import FindingFixStrictnessSettings, Severity
from orchestrator.workflow.universal_critique import EffectiveUniversalCritique

NON_DICT_FS_VALUES: tuple[Any, ...] = ([], "string", 123, 1.5, True, False)


def _validate_a1_high_true(_case: dict[str, Any], ctx: dict[str, Any]) -> None:
    assert "finding_fix_strictness" in ctx
    fs_obj = ctx["finding_fix_strictness"]
    assert isinstance(fs_obj, FindingFixStrictnessSettings)
    assert fs_obj.minimum_severity_requiring_fixes == Severity.HIGH
    assert fs_obj.also_require_fixes_for_low_severity is True


def _validate_a2_empty_defaults(_case: dict[str, Any], ctx: dict[str, Any]) -> None:
    fs_a2 = ctx["finding_fix_strictness"]
    assert isinstance(fs_a2, FindingFixStrictnessSettings)
    assert fs_a2.minimum_severity_requiring_fixes == Severity.MEDIUM
    assert fs_a2.also_require_fixes_for_low_severity is False


def _validate_b1_bare_default(_case: dict[str, Any], ctx: dict[str, Any]) -> None:
    fs_b1 = ctx.get("finding_fix_strictness")
    assert isinstance(fs_b1, FindingFixStrictnessSettings)
    assert fs_b1.minimum_severity_requiring_fixes == Severity.MEDIUM
    assert fs_b1.also_require_fixes_for_low_severity is False


def _validate_b2_overrides(_case: dict[str, Any], ctx: dict[str, Any]) -> None:
    fs_b2 = ctx["finding_fix_strictness"]
    assert fs_b2.minimum_severity_requiring_fixes == Severity.BLOCKER
    assert fs_b2.also_require_fixes_for_low_severity is True


def _validate_b4_single_snapshot_call(case: dict[str, Any], _actual: Any) -> None:
    mock_snap = case["mock_snap"]
    assert mock_snap.call_count == 1
    assert mock_snap.call_args.args == (case["rid"],)


def _validate_b5_fresh_instances(_case: dict[str, Any], ctx_pair: tuple[dict[str, Any], dict[str, Any]]) -> None:
    ctx_first, ctx_second = ctx_pair
    assert ctx_first == ctx_second
    assert ctx_first["finding_fix_strictness"] is not ctx_second["finding_fix_strictness"]


def _validate_c1_no_rows(_case: dict[str, Any], captured: dict[str, Any]) -> None:
    assert captured["wf"] is None
    assert isinstance(captured["result"], EffectiveUniversalCritique)


def _validate_c2_default_profile(_case: dict[str, Any], captured: dict[str, Any]) -> None:
    assert captured["wf"] == "default"
    assert isinstance(captured["wf"], str)


def _validate_c3_real_call(_case: dict[str, Any], result: EffectiveUniversalCritique) -> None:
    assert isinstance(result, EffectiveUniversalCritique)


def _validate_c4_int_coercion(_case: dict[str, Any], captured: dict[str, Any]) -> None:
    assert captured["wf"] == "123"
    assert isinstance(captured["wf"], str)


def _validate_c5_first_wins(_case: dict[str, Any], captured: dict[str, Any]) -> None:
    assert captured["wf"] == "first"


def _validate_d1_list_run_events(case: dict[str, Any], _actual: Any) -> None:
    mock_lre = case["mock_lre"]
    rid = case["rid"]
    assert mock_lre.call_count == 2
    for i, call in enumerate(mock_lre.call_args_list):
        assert call.args == (str(rid),), f"call {i}"


def _validate_d2_facet_independence(case: dict[str, Any], _actual: Any) -> None:
    fs_d2 = case["ctx"]["finding_fix_strictness"]
    assert fs_d2.minimum_severity_requiring_fixes == Severity.HIGH
    assert case["captured"]["wf"] == "default"


def _validate_d3_read_only(case: dict[str, Any], _actual: Any) -> None:
    assert case["rows_after"] == case["rows_before"]


def _validate_d4_repo_root(_case: dict[str, Any], captured: dict[str, Any]) -> None:
    assert captured["repo_root"] == captured["orch_repo_root"]


def _validate_d5_asymmetric_errors(_case: dict[str, Any], result: EffectiveUniversalCritique) -> None:
    assert isinstance(result, EffectiveUniversalCritique)


STRICTNESS_FS_VALUE_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "a1_high_true",
        "policy_snapshot": {
            "finding_fix_strictness": {
                "minimum_severity_requiring_fixes": "HIGH",
                "also_require_fixes_for_low_severity": True,
            }
        },
        "validate": _validate_a1_high_true,
    },
    {
        "case_id": "a2_empty_defaults",
        "policy_snapshot": {"finding_fix_strictness": {}},
        "validate": _validate_a2_empty_defaults,
    },
)

STRICTNESS_FS_EXCEPTION_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "a3_bad_enum",
        "policy_snapshot": {"finding_fix_strictness": {"minimum_severity_requiring_fixes": "BOGUS"}},
        "exc_type": ValidationError,
        "msg_contains": ("FindingFixStrictnessSettings",),
    },
    {
        "case_id": "a3_extra_key",
        "policy_snapshot": {"finding_fix_strictness": {"unknown_field": True}},
        "exc_type": ValidationError,
        "msg_contains": ("FindingFixStrictnessSettings",),
    },
    {
        "case_id": "a3_wrong_type",
        "policy_snapshot": {"finding_fix_strictness": {"also_require_fixes_for_low_severity": "not-a-bool"}},
        "exc_type": ValidationError,
        "msg_contains": ("FindingFixStrictnessSettings",),
    },
)

STRICTNESS_FS_EMPTY_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "a4_missing_key", "policy_snapshot": {}, "expected": {}},
    {"case_id": "a4_explicit_none", "policy_snapshot": {"finding_fix_strictness": None}, "expected": {}},
    *(
        {"case_id": f"a5_non_dict_{type(v).__name__}", "policy_snapshot": {"finding_fix_strictness": v}, "expected": {}}
        for v in NON_DICT_FS_VALUES
    ),
)

STRICTNESS_REAL_PATH_VALUE_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "b1_bare_default", "setup": "create_run_default", "validate": _validate_b1_bare_default},
    {
        "case_id": "b2_overrides",
        "setup": "create_run_overrides",
        "run_policy_overrides": {
            "finding_fix_strictness": {
                "minimum_severity_requiring_fixes": "BLOCKER",
                "also_require_fixes_for_low_severity": True,
            }
        },
        "validate": _validate_b2_overrides,
    },
    {"case_id": "b3_unknown_rid", "setup": "unknown_rid", "expected": {}},
)

STRICTNESS_SNAPSHOT_WIRING_CASE: dict[str, Any] = {
    "case_id": "b4_single_snapshot_call",
    "setup": "create_run_default",
    "validate": _validate_b4_single_snapshot_call,
}

STRICTNESS_IDEMPOTENCY_CASE: dict[str, Any] = {
    "case_id": "b5_fresh_instances",
    "setup": "create_run_default",
    "validate": _validate_b5_fresh_instances,
}

EUC_SEAM_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "c1_no_rows", "setup": "no_rows", "validate": _validate_c1_no_rows},
    {"case_id": "c2_default_profile", "setup": "create_run_default", "validate": _validate_c2_default_profile},
    {"case_id": "c3_real_call", "setup": "no_rows", "validate": _validate_c3_real_call},
    {"case_id": "c4_int_coercion", "setup": "inject_int_profile", "validate": _validate_c4_int_coercion},
    {"case_id": "c5_first_wins", "setup": "inject_two_profiles", "validate": _validate_c5_first_wins},
)

CROSS_HELPER_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "d1_list_run_events", "setup": "dual_call", "validate": _validate_d1_list_run_events},
    {"case_id": "d2_facet_independence", "setup": "strictness_and_euc", "validate": _validate_d2_facet_independence},
    {"case_id": "d3_read_only", "setup": "dual_call_readonly", "validate": _validate_d3_read_only},
    {"case_id": "d4_repo_root", "setup": "euc_no_rows", "validate": _validate_d4_repo_root},
    {"case_id": "d5_asymmetric_errors", "setup": "bad_strictness_euc_ok", "validate": _validate_d5_asymmetric_errors},
)
