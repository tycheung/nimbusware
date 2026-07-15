from __future__ import annotations

from pathlib import Path
from typing import Any

from standards.fs_walk import iter_workspace_files
from standards.stream_results import CheckResult


def check_loc_budget(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    from env import find_repo_root

    root = find_repo_root(start=workspace)
    if root != workspace.resolve():
        return CheckResult(
            check_id="hygiene.loc_budget",
            passed=True,
            verdict="critique",
            detail="skipped outside monorepo",
            exit_code=0,
        )
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "scripts/ci/run_loc_budget_ci_gate.py"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return CheckResult(
        check_id="hygiene.loc_budget",
        passed=proc.returncode == 0,
        verdict="critique",
        detail=(proc.stdout or proc.stderr or "")[:4000],
        exit_code=proc.returncode,
    )


def check_module_line_cap(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    max_lines = int(params.get("max_lines") or 1000)
    hits: list[str] = []
    for path in iter_workspace_files(workspace, suffix=".py"):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > max_lines:
            hits.append(f"{path.relative_to(workspace)}: {len(lines)}")
    return CheckResult(
        check_id="hygiene.module_line_cap",
        passed=not hits,
        verdict="critique",
        detail="; ".join(hits[:20]) or "ok",
        exit_code=0 if not hits else 1,
    )
