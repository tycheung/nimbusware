from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.micro_slice import SlicePlan
from nimbusware_orchestrator.patch_context import (
    maven_test_class_from_failing_test,
    patch_context_from_run_rows,
    resolve_patch_test_targets,
)
from nimbusware_orchestrator.verifiers import (
    run_go_test,
    run_mvn_test,
    run_pytest_targets,
    run_ruff_on_paths,
)


def _workspace_stack(workspace: Path) -> str:
    if (workspace / "go.mod").is_file():
        return "go"
    if (workspace / "pom.xml").is_file():
        return "jvm"
    return "python"


def run_slice_verify_and_test(
    workspace: Path,
    plan: SlicePlan,
    *,
    timeout_seconds: float,
    rows: list[dict[str, Any]] | None = None,
) -> tuple[bool, str, bool, str]:
    stack = _workspace_stack(workspace)
    missing = [p for p in plan.target_paths if not (workspace / p).is_file()]
    sections: list[str] = []
    verify_ok = True
    if missing:
        verify_ok = False
        sections.append(f"missing target files: {missing}")
    py_targets = [p for p in plan.target_paths if p.endswith(".py")]
    if stack == "python" and py_targets:
        ruff_code, ruff_out = run_ruff_on_paths(
            workspace,
            py_targets,
            timeout_seconds=timeout_seconds,
        )
        sections.append(f"=== ruff (exit {ruff_code}) ===\n{ruff_out}")
        if ruff_code != 0:
            verify_ok = False
    else:
        sections.append("=== ruff skipped (non-Python stack) ===\n")
    patch_ctx = patch_context_from_run_rows(rows or [])
    test_targets = resolve_patch_test_targets(plan.target_paths, patch_ctx)
    if stack == "go":
        test_code, test_out = run_go_test(workspace, timeout_seconds=timeout_seconds)
        tests_passed = test_code == 0
        sections.append(f"=== go test (exit {test_code}) ===\n{test_out}")
    elif stack == "jvm":
        selector = None
        if patch_ctx:
            failing = str(patch_ctx.get("failing_test") or "").strip()
            selector = maven_test_class_from_failing_test(failing)
        mvn_timeout = max(timeout_seconds, 300.0)
        test_code, test_out = run_mvn_test(
            workspace,
            timeout_seconds=mvn_timeout,
            test_selector=selector,
        )
        if test_code != 0 and selector:
            fallback_code, fallback_out = run_mvn_test(
                workspace,
                timeout_seconds=mvn_timeout,
                test_selector=None,
            )
            sections.append(
                f"=== mvn test targeted (exit {test_code}) ===\n{test_out}\n"
                f"=== mvn test fallback full (exit {fallback_code}) ===\n{fallback_out}",
            )
            test_code, test_out = fallback_code, fallback_out
        else:
            sections.append(f"=== mvn test (exit {test_code}) ===\n{test_out}")
        tests_passed = test_code == 0
    else:
        existing_tests = [t for t in test_targets if (workspace / t).is_file()]
        if existing_tests:
            test_code, test_out = run_pytest_targets(
                workspace,
                existing_tests,
                timeout_seconds=timeout_seconds,
            )
            tests_passed = test_code == 0
        else:
            test_code, test_out = 0, "no mapped test files; skipped\n"
            tests_passed = True
        sections.append(f"=== pytest (exit {test_code}) ===\n{test_out}")
    return verify_ok, "\n".join(sections), tests_passed, test_out
