from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


def poll_github_workflow_run(
    *,
    github_repo: str,
    workflow_path: str = "",
    branch: str = "",
) -> dict[str, Any]:
    repo = github_repo.strip()
    if not repo:
        return {"status": "skipped", "reason": "github_repo_required"}
    if shutil.which("gh") is None:
        return {"status": "skipped", "reason": "gh_not_found"}

    cmd = [
        "gh",
        "run",
        "list",
        "--repo",
        repo,
        "--limit",
        "1",
        "--json",
        "status,conclusion,url,databaseId,workflowName,headBranch",
    ]
    wf = workflow_path.strip()
    if wf:
        cmd.extend(["--workflow", wf])
    branch_name = branch.strip()
    if branch_name:
        cmd.extend(["--branch", branch_name])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "error", "reason": str(exc)[:200]}

    if proc.returncode != 0:
        return {
            "status": "failed",
            "detail": (proc.stderr or proc.stdout or "gh run list failed")[:500],
            "exit_code": proc.returncode,
        }

    raw = (proc.stdout or "").strip()
    if not raw:
        return {"status": "skipped", "detail": "no workflow runs found"}

    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "error", "detail": "invalid gh json output"}

    if not isinstance(rows, list) or not rows:
        return {"status": "skipped", "detail": "no workflow runs found"}

    row = rows[0] if isinstance(rows[0], dict) else {}
    gh_status = str(row.get("status") or "").lower()
    conclusion = str(row.get("conclusion") or "").lower()
    run_url = str(row.get("url") or "").strip()
    workflow_name = str(row.get("workflowName") or "").strip()
    run_id = row.get("databaseId")

    detail_parts = [part for part in (workflow_name, gh_status, conclusion) if part]
    detail = " · ".join(detail_parts) or gh_status or "unknown"

    if gh_status in {"queued", "in_progress", "waiting", "pending", "requested"}:
        return {
            "status": "running",
            "detail": detail,
            "run_url": run_url,
            "workflow_run_id": run_id,
            "github_status": gh_status,
        }
    if conclusion == "success" or gh_status == "completed" and conclusion in {"", "success"}:
        return {
            "status": "passed",
            "detail": detail,
            "run_url": run_url,
            "workflow_run_id": run_id,
            "github_status": gh_status,
        }
    if conclusion in {"failure", "cancelled", "timed_out", "action_required", "stale"}:
        return {
            "status": "failed",
            "detail": detail,
            "run_url": run_url,
            "workflow_run_id": run_id,
            "github_status": gh_status,
            "conclusion": conclusion,
        }
    return {
        "status": "running" if gh_status else "skipped",
        "detail": detail,
        "run_url": run_url,
        "workflow_run_id": run_id,
        "github_status": gh_status,
        "conclusion": conclusion,
    }
