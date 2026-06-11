from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.micro_slice import SlicePlan
from nimbusware_orchestrator.patch_context import (
    patch_context_from_run_rows,
    resolve_patch_test_targets,
)
from nimbusware_orchestrator.verifiers import run_pytest_targets, run_ruff_on_paths


def run_slice_verify_and_test(
    workspace: Path,
    plan: SlicePlan,
    *,
    timeout_seconds: float,
    rows: list[dict[str, Any]] | None = None,
) -> tuple[bool, str, bool, str]:
    missing = [p for p in plan.target_paths if not (workspace / p).is_file()]
    sections: list[str] = []
    verify_ok = True
    if missing:
        verify_ok = False
        sections.append(f"missing target files: {missing}")
    ruff_code, ruff_out = run_ruff_on_paths(
        workspace,
        list(plan.target_paths),
        timeout_seconds=timeout_seconds,
    )
    sections.append(f"=== ruff (exit {ruff_code}) ===\n{ruff_out}")
    if ruff_code != 0:
        verify_ok = False
    patch_ctx = patch_context_from_run_rows(rows or [])
    test_targets = resolve_patch_test_targets(plan.target_paths, patch_ctx)
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
