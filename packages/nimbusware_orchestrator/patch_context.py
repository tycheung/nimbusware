from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from agent_core.mapping import mapping_or_empty

if TYPE_CHECKING:
    from nimbusware_orchestrator.micro_slice import SlicePlan


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
    return normalize_patch_context(
        mapping_or_empty(rows[0].get("metadata")).get("patch_context"),
    )


def patch_effective_from_run_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    eff = mapping_or_empty(mapping_or_empty(rows[0].get("metadata")).get("patch_effective"))
    return eff or None


def work_type_from_run_rows(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    wt = str(mapping_or_empty(rows[0].get("metadata")).get("work_type") or "").strip().lower()
    return wt or None


def is_patch_run(rows: list[dict[str, Any]]) -> bool:
    wt = work_type_from_run_rows(rows)
    if wt == "patch":
        return True
    patch_eff = patch_effective_from_run_rows(rows)
    return bool(patch_eff and patch_eff.get("enabled"))


def _workspace_stack(workspace: Path) -> str:
    if (workspace / "go.mod").is_file():
        return "go"
    if (workspace / "pom.xml").is_file():
        return "jvm"
    return "python"


def implementation_path_from_failing_test(failing_test: str, *, stack: str) -> str | None:
    path = failing_test.replace("\\", "/").strip()
    if not path:
        return None
    if stack == "go" and path.endswith("_test.go"):
        return f"{path[:-len('_test.go')]}.go"
    if stack == "jvm" and "src/test/java/" in path and path.endswith("Test.java"):
        return path.replace("src/test/java/", "src/main/java/").removesuffix("Test.java") + ".java"
    if stack == "python" and path.startswith("tests/") and path.endswith(".py"):
        stem = Path(path).stem
        if stem.startswith("test_"):
            module = stem.removeprefix("test_")
            return f"src/{module}.py"
    return None


def infer_patch_implementation_paths(
    patch_ctx: dict[str, Any] | None,
    workspace: Path,
) -> tuple[str, ...]:
    if patch_ctx:
        paths = patch_ctx.get("target_paths")
        if isinstance(paths, list) and paths:
            return tuple(str(p).strip() for p in paths[:3] if str(p).strip())
        failing = str(patch_ctx.get("failing_test") or "").strip()
        if failing:
            impl = implementation_path_from_failing_test(
                failing,
                stack=_workspace_stack(workspace),
            )
            if impl and (workspace / impl).is_file():
                return (impl,)

    stack = _workspace_stack(workspace)
    if stack == "go":
        for candidate in sorted(workspace.glob("*.go")):
            if not candidate.name.endswith("_test.go"):
                return (candidate.name,)
    elif stack == "jvm":
        for candidate in sorted(workspace.glob("src/main/java/**/*.java")):
            return (candidate.relative_to(workspace).as_posix(),)
    return ()


def patch_slice_plan_for_run(
    slice_index: int,
    rows: list[dict[str, Any]],
    workspace: Path,
) -> "SlicePlan | None":
    if not is_patch_run(rows):
        return None
    target_paths = infer_patch_implementation_paths(patch_context_from_run_rows(rows), workspace)
    if not target_paths:
        return None
    from nimbusware_orchestrator.micro_slice import SlicePlan, parse_slice_plan

    return parse_slice_plan(
        {
            "slice_id": f"slice-{slice_index}",
            "rationale": "Patch lane scoped plan from failing test or workspace stack",
            "target_paths": list(target_paths),
            "acceptance_criteria": "Scoped stack tests pass",
        },
    )


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
