from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.patch_context import (
    maven_test_class_from_failing_test,
    patch_context_from_run_rows,
    resolve_patch_test_targets,
)
from orchestrator.profiles.enforcement_profiles import EnforcementProfile
from orchestrator.slice.micro_slice import SlicePlan
from orchestrator.verifiers import (
    run_go_test,
    run_mvn_test,
    run_pytest_targets,
    run_ruff_on_paths,
)
from orchestrator.workspace_ci_runner import run_enforcement_bundle
from standards.profile import standards_platform_enabled
from standards.workspace_standards import format_standards_log, run_workspace_standards


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
    enforcement_profile: EnforcementProfile | None = None,
) -> tuple[bool, str, bool, str]:
    if enforcement_profile is not None:
        bundle = run_enforcement_bundle(
            workspace,
            enforcement_profile,
            scope_paths=list(plan.target_paths),
            milestone=False,
            timeout_seconds=timeout_seconds,
        )
        verify_ok = bundle.passed
        bundle_sections = [
            f"=== enforcement depth {enforcement_profile.level} ({enforcement_profile.name}) ===",
        ]
        for step in bundle.steps:
            bundle_sections.append(f"=== {step.name} (exit {step.exit_code}) ===\n{step.detail}")
        tests_passed = verify_ok
        test_out = bundle_sections[-1] if bundle_sections else ""
        for step in bundle.steps:
            if step.name.startswith("pytest"):
                tests_passed = step.exit_code == 0 and not (
                    enforcement_profile.tests_mode == "mapped_required" and step.skipped
                )
                test_out = step.detail
                break
        if standards_platform_enabled():
            std_ok, std_results = run_workspace_standards(
                workspace,
                enforcement_level=enforcement_profile.level,
            )
            if std_results:
                bundle_sections.append(format_standards_log(std_results))
            if not std_ok:
                verify_ok = False
        return verify_ok, "\n".join(bundle_sections), tests_passed, test_out

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
