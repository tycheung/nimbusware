"""Optional per-slice git commit after gate PASS (fo410)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from hermes_orchestrator.git_outputs import run_branch_name, slice_commit_message
from hermes_orchestrator.micro_slice import SlicePlan


def slice_auto_commit_enabled(run_metadata: dict[str, Any]) -> bool:
    slice_meta = run_metadata.get("slice")
    if isinstance(slice_meta, dict) and slice_meta.get("auto_commit_per_slice") is True:
        return True
    raw = os.environ.get("HERMES_SLICE_AUTO_COMMIT", "").strip().lower()
    return raw in ("1", "true", "yes")


def maybe_commit_slice(
    workspace: Path,
    plan: SlicePlan,
    *,
    run_id: str,
    run_metadata: dict[str, Any],
) -> dict[str, Any]:
    if not slice_auto_commit_enabled(run_metadata):
        return {"status": "skipped", "reason": "disabled"}
    if not (workspace / ".git").is_dir():
        return {"status": "skipped", "reason": "not_git_repo"}
    branch = run_branch_name(run_id)
    try:
        subprocess.run(
            ["git", "checkout", "-B", branch],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        subprocess.run(
            ["git", "add", "-A"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        proc = subprocess.run(
            ["git", "commit", "-m", slice_commit_message(plan)],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0 and "nothing to commit" in (proc.stderr or proc.stdout or ""):
            return {"status": "skipped", "reason": "nothing_to_commit"}
        return {
            "status": "committed" if proc.returncode == 0 else "failed",
            "branch": branch,
            "exit_code": proc.returncode,
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "error", "reason": str(exc)[:200]}
