from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_orchestrator.micro_slice import SlicePlan
from nimbusware_env.env_flags import (
    nimbusware_git_native_outputs_enabled,
    nimbusware_git_pr_on_complete_enabled,
    nimbusware_slice_branch_prefix,
)


def run_branch_name(run_id: str | UUID, *, prefix: str | None = None) -> str:
    rid = str(run_id)
    pfx = (prefix or nimbusware_slice_branch_prefix()).strip()
    if not pfx:
        pfx = "nimbusware/run-"
    return f"{pfx}{rid}"


def git_native_outputs_enabled(run_metadata: dict[str, Any]) -> bool:
    git_meta = run_metadata.get("git")
    if isinstance(git_meta, dict) and git_meta.get("native_outputs") is True:
        return True
    return nimbusware_git_native_outputs_enabled()


def gh_pr_on_complete_enabled(run_metadata: dict[str, Any]) -> bool:
    git_meta = run_metadata.get("git")
    if isinstance(git_meta, dict) and git_meta.get("open_pr_on_complete") is True:
        return True
    return nimbusware_git_pr_on_complete_enabled()


def slice_commit_message(plan: SlicePlan) -> str:
    msg = (plan.rationale or plan.slice_id)[:200]
    return f"[nimbusware] {plan.slice_id}: {msg}"


def run_complete_commit_message(run_id: str | UUID, *, slice_count: int) -> str:
    return f"[nimbusware] run {run_id} complete ({slice_count} slice(s) passed gates)"


def ensure_run_branch(workspace: Path, run_id: str | UUID) -> dict[str, Any]:
    if not (workspace / ".git").is_dir():
        return {"status": "skipped", "reason": "not_git_repo"}
    branch = run_branch_name(run_id)
    try:
        proc = subprocess.run(
            ["git", "checkout", "-B", branch],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return {
            "status": "ok" if proc.returncode == 0 else "failed",
            "branch": branch,
            "exit_code": proc.returncode,
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "error", "reason": str(exc)[:200]}


def maybe_open_gh_pr(
    workspace: Path,
    run_id: str | UUID,
    *,
    title: str | None = None,
    body: str | None = None,
) -> dict[str, Any]:
    if shutil.which("gh") is None:
        return {"status": "skipped", "reason": "gh_not_found"}
    if not (workspace / ".git").is_dir():
        return {"status": "skipped", "reason": "not_git_repo"}
    branch = run_branch_name(run_id)
    pr_title = title or f"Nimbusware run {run_id}"
    pr_body = body or f"Automated PR for Nimbusware run `{run_id}`."
    try:
        proc = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--head",
                branch,
                "--title",
                pr_title,
                "--body",
                pr_body,
            ],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if proc.returncode != 0:
            return {
                "status": "failed",
                "exit_code": proc.returncode,
                "stderr": (proc.stderr or "")[:500],
            }
        url = (proc.stdout or "").strip()
        return {"status": "created", "branch": branch, "pr_url": url}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "error", "reason": str(exc)[:200]}


def maybe_finalize_git_outputs(
    workspace: Path,
    run_id: str | UUID,
    run_metadata: dict[str, Any],
    *,
    slice_count: int,
) -> dict[str, Any]:
    if not git_native_outputs_enabled(run_metadata):
        return {"status": "skipped", "reason": "disabled"}
    out: dict[str, Any] = {"branch": run_branch_name(run_id)}
    branch_result = ensure_run_branch(workspace, run_id)
    out["branch_checkout"] = branch_result
    if branch_result.get("status") != "ok":
        return out
    if not (workspace / ".git").is_dir():
        return out
    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        proc = subprocess.run(
            ["git", "commit", "-m", run_complete_commit_message(run_id, slice_count=slice_count)],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        out["final_commit"] = {
            "status": "committed" if proc.returncode == 0 else "failed",
            "exit_code": proc.returncode,
        }
    except (OSError, subprocess.SubprocessError) as exc:
        out["final_commit"] = {"status": "error", "reason": str(exc)[:200]}
    if gh_pr_on_complete_enabled(run_metadata):
        out["pr"] = maybe_open_gh_pr(workspace, run_id)
    return out


def emit_git_finalize_after_micro_slice_pass(
    orch: Any,
    run_id: UUID,
    workspace: Path,
    results: list[Any],
    *,
    emit_stage: Any,
) -> None:
    if not results or not all(getattr(g, "passed", False) for g in results):
        return
    run_meta = orch._run_created_metadata(run_id)
    git_out = maybe_finalize_git_outputs(
        workspace,
        run_id,
        run_meta,
        slice_count=len(results),
    )
    if git_out.get("status") != "skipped":
        emit_stage(orch, run_id, "slice.git_finalize", metadata=git_out)
