from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from orchestrator.enforcement_profiles import EnforcementProfile
from orchestrator.verifiers import (
    run_bandit_on_layout,
    run_go_test,
    run_mvn_test,
    run_mypy_on_layout,
    run_pip_audit,
    run_pytest,
    run_pytest_targets,
    run_ruff_check,
    run_ruff_format_check,
    run_ruff_on_paths,
)
from orchestrator.workspace_layout import (
    WorkspaceLayout,
    detect_workspace_layout,
    resolve_ruff_targets,
)

PARITY_LEVEL = 10


@dataclass(frozen=True)
class EnforcementStep:
    name: str
    exit_code: int
    detail: str = ""
    skipped: bool = False

    @property
    def verdict(self) -> str:
        if self.skipped:
            return "SKIP"
        return "PASS" if self.exit_code == 0 else "FAIL"


@dataclass
class EnforcementResult:
    passed: bool
    exit_code: int
    steps: list[EnforcementStep] = field(default_factory=list)
    layout: WorkspaceLayout | None = None

    def to_metadata(self) -> dict[str, Any]:
        return {
            "enforcement_passed": self.passed,
            "enforcement_exit_code": self.exit_code,
            "enforcement_steps": [
                {
                    "name": s.name,
                    "verdict": s.verdict,
                    "exit_code": s.exit_code,
                    "detail": s.detail[:500],
                    "skipped": s.skipped,
                }
                for s in self.steps
            ],
            "workspace_layout": self.layout.to_dict() if self.layout else None,
        }


def parity_contract_steps() -> tuple[str, ...]:
    return (
        "ruff_check",
        "ruff_format",
        "ruff_workspace",
        "pytest_coverage",
        "bandit",
        "pip_audit",
        "mypy",
    )


def _coverage_args(layout: WorkspaceLayout, floor: float | None) -> list[str]:
    effective = floor if floor is not None else layout.coverage_floor
    if effective is None:
        return []
    pct = effective * 100.0 if effective <= 1.0 else effective
    return ["--cov=.", f"--cov-fail-under={pct:.0f}"]


def run_enforcement_bundle(
    workspace: Path,
    profile: EnforcementProfile,
    *,
    scope_paths: list[str] | None = None,
    milestone: bool = False,
    timeout_seconds: float = 300.0,
) -> EnforcementResult:
    layout = detect_workspace_layout(workspace)
    steps: list[EnforcementStep] = []
    worst = 0

    if profile.ruff_scope != "off" and layout.stack == "python":
        targets = resolve_ruff_targets(layout, scope_paths=scope_paths, scope=profile.ruff_scope)
        if targets:
            rel = [str(t.relative_to(layout.workspace)) for t in targets]
            code, out = run_ruff_on_paths(layout.workspace, rel, timeout_seconds=timeout_seconds)
        else:
            code, out = 0, "ruff skipped (no targets)\n"
        steps.append(EnforcementStep("ruff_check", code, out[:2000]))
        worst = max(worst, code)
        if profile.ruff_format_check:
            fmt_code, fmt_out = run_ruff_format_check(
                layout.workspace,
                [str(t) for t in targets] if targets else None,
                timeout_seconds=timeout_seconds,
            )
            steps.append(EnforcementStep("ruff_format", fmt_code, fmt_out[:2000]))
            worst = max(worst, fmt_code)

    run_full_tests = profile.tests_mode in ("full", "full_with_coverage") or (
        milestone and profile.milestone_full_ci
    )
    if layout.stack == "go":
        code, out = run_go_test(layout.workspace, timeout_seconds=timeout_seconds)
        steps.append(EnforcementStep("go_test", code, out[:2000]))
        worst = max(worst, code)
    elif layout.stack == "jvm":
        code, out = run_mvn_test(layout.workspace, timeout_seconds=max(timeout_seconds, 300.0))
        steps.append(EnforcementStep("mvn_test", code, out[:2000]))
        worst = max(worst, code)
    elif run_full_tests:
        extra: list[str] = []
        if profile.tests_mode == "full_with_coverage" or profile.coverage_floor is not None:
            extra = _coverage_args(layout, profile.coverage_floor)
        if extra:
            proc = subprocess.run(
                ["pytest", "-q", *extra],
                cwd=layout.workspace,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            out = ((proc.stdout or "") + (proc.stderr or ""))[:2000]
            steps.append(EnforcementStep("pytest_coverage", proc.returncode, out))
            worst = max(worst, proc.returncode)
        else:
            code, out = run_pytest(layout.workspace, timeout_seconds=timeout_seconds)
            steps.append(EnforcementStep("pytest", code, out[:2000]))
            worst = max(worst, code)
    elif scope_paths and profile.tests_mode == "mapped_required":
        from orchestrator.slice_gate import map_paths_to_test_targets

        mapped = map_paths_to_test_targets(tuple(scope_paths))
        existing = [t for t in mapped if (layout.workspace / t).is_file()]
        if existing:
            code, out = run_pytest_targets(
                layout.workspace,
                existing,
                timeout_seconds=timeout_seconds,
            )
            steps.append(EnforcementStep("pytest_mapped", code, out[:2000]))
            worst = max(worst, code)
        else:
            fail_missing = (
                profile.tests_mode == "mapped_required" or profile.skip_verdict_policy == "fail"
            )
            steps.append(
                EnforcementStep(
                    "pytest_mapped",
                    1 if fail_missing else 0,
                    "no mapped test files",
                    skipped=not fail_missing,
                ),
            )
            if fail_missing:
                worst = max(worst, 1)

    if profile.security_mode != "off" and layout.stack == "python":
        if profile.security_mode in ("bandit", "full_scan"):
            b_code, b_out = run_bandit_on_layout(layout, timeout_seconds=timeout_seconds)
            steps.append(EnforcementStep("bandit", b_code, b_out[:2000]))
            worst = max(worst, b_code)
        if profile.security_mode == "full_scan":
            r_code, r_out = run_ruff_check(layout.workspace, timeout_seconds=timeout_seconds)
            steps.append(EnforcementStep("ruff_workspace", r_code, r_out[:2000]))
            worst = max(worst, r_code)
            if layout.has_mypy_config:
                m_code, m_out = run_mypy_on_layout(layout, timeout_seconds=timeout_seconds)
                steps.append(EnforcementStep("mypy", m_code, m_out[:2000]))
                worst = max(worst, m_code)

    pip_required = profile.pip_audit == "required" or (
        profile.pip_audit == "if_lockfile"
        and (layout.has_poetry_lock or layout.has_requirements_lock)
    )
    if pip_required and shutil.which("pip-audit"):
        p_code, p_out = run_pip_audit(layout.workspace, timeout_seconds=timeout_seconds)
        steps.append(
            EnforcementStep(
                "pip_audit", p_code, p_out[:2000], skipped=p_code == 0 and not p_out.strip()
            )
        )
        worst = max(worst, p_code)
    elif profile.pip_audit == "required":
        steps.append(EnforcementStep("pip_audit", 1, "pip-audit not on PATH"))
        worst = max(worst, 1)

    passed = worst == 0
    return EnforcementResult(passed=passed, exit_code=worst, steps=steps, layout=layout)


def run_workspace_ci_parity(
    workspace: Path, *, timeout_seconds: float = 600.0
) -> EnforcementResult:
    from orchestrator.enforcement_profiles import preset_for_enforcement_level

    profile = preset_for_enforcement_level(PARITY_LEVEL)
    return run_enforcement_bundle(
        workspace,
        profile,
        milestone=True,
        timeout_seconds=timeout_seconds,
    )
