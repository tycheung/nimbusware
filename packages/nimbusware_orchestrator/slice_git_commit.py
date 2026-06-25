from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from nimbusware_env.env_flags import nimbusware_slice_auto_commit_enabled
from nimbusware_iam.context import get_auth_context
from nimbusware_orchestrator.fleet_commit_policy import tenant_commit_policy
from nimbusware_orchestrator.git_outputs import run_branch_name, slice_commit_message
from nimbusware_orchestrator.micro_slice import SlicePlan


def slice_auto_commit_enabled(run_metadata: dict[str, Any]) -> bool:
    slice_meta = run_metadata.get("slice")
    if isinstance(slice_meta, dict) and slice_meta.get("auto_commit_per_slice") is True:
        return True
    ctx = get_auth_context()
    tenant_slug = ctx.tenant_slug if ctx else None
    policy = tenant_commit_policy(tenant_slug)
    if policy.require_auto_commit:
        return True
    return nimbusware_slice_auto_commit_enabled()


def _commit_message_allowed(message: str, regex: str) -> bool:
    pattern = regex.strip()
    if not pattern:
        return True
    try:
        return re.search(pattern, message) is not None
    except re.error:
        return True


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
    ctx = get_auth_context()
    commit_policy = tenant_commit_policy(ctx.tenant_slug if ctx else None)
    message = slice_commit_message(plan)
    if not _commit_message_allowed(message, commit_policy.message_regex):
        return {
            "status": "skipped",
            "reason": "message_regex_mismatch",
            "message_regex": commit_policy.message_regex,
        }
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
            ["git", "commit", "-m", message],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0 and "nothing to commit" in (proc.stderr or proc.stdout or ""):
            return {"status": "skipped", "reason": "nothing_to_commit"}
        sha = ""
        if proc.returncode == 0:
            rev = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if rev.returncode == 0:
                sha = (rev.stdout or "").strip()
        return {
            "status": "committed" if proc.returncode == 0 else "failed",
            "branch": branch,
            "sha": sha,
            "exit_code": proc.returncode,
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "error", "reason": str(exc)[:200]}
