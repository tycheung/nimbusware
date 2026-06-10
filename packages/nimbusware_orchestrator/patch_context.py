from __future__ import annotations

from typing import Any


def normalize_patch_context(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    out: dict[str, Any] = {}
    paths = raw.get("target_paths")
    if isinstance(paths, list):
        out["target_paths"] = [str(p).strip() for p in paths if str(p).strip()][:8]
    failing = str(raw.get("failing_test") or "").strip()
    if failing:
        out["failing_test"] = failing[:500]
    trace = str(raw.get("stack_trace") or "").strip()
    if trace:
        out["stack_trace"] = trace[:4000]
    snippet = str(raw.get("error_snippet") or "").strip()
    if snippet:
        out["error_snippet"] = snippet[:2000]
    return out or None


def patch_context_from_run_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    meta = rows[0].get("metadata")
    if not isinstance(meta, dict):
        return None
    return normalize_patch_context(meta.get("patch_context"))


def patch_effective_from_run_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    meta = rows[0].get("metadata")
    if not isinstance(meta, dict):
        return None
    eff = meta.get("patch_effective")
    return eff if isinstance(eff, dict) else None


def work_type_from_run_rows(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    meta = rows[0].get("metadata")
    if not isinstance(meta, dict):
        return None
    wt = str(meta.get("work_type") or "").strip().lower()
    return wt or None


def resolve_patch_test_targets(
    plan_target_paths: tuple[str, ...],
    patch_ctx: dict[str, Any] | None,
) -> list[str]:
    if patch_ctx:
        failing = str(patch_ctx.get("failing_test") or "").strip()
        if failing:
            return [failing]
    from nimbusware_orchestrator.slice_gate import map_paths_to_test_targets

    return map_paths_to_test_targets(plan_target_paths)


def patch_auto_apply_allowed(
    *,
    policy: dict[str, Any],
    files_changed: int,
    loc_changed: int,
    tests_passed: bool,
    gate_passed: bool,
) -> bool:
    if not gate_passed:
        return False
    max_loc = int(policy.get("max_loc", 40))
    max_files = int(policy.get("max_files", 1))
    if files_changed > max_files or loc_changed > max_loc:
        return False
    if bool(policy.get("require_tests_passed", True)) and not tests_passed:
        return False
    return True
