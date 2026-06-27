from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root


def _user_path(repo_root: Path, user_id: str) -> Path:
    return repo_root / "configs" / "deploy" / "users" / f"{user_id.strip()}.yaml"


def load_deploy_credentials(
    user_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        return {"user_id": "", "aws_profile": "", "github_repo": "", "workflow_path": ""}
    root = repo_root or find_repo_root()
    path = _user_path(root, uid)
    if not path.is_file():
        return {"user_id": uid, "aws_profile": "", "github_repo": "", "workflow_path": ""}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {"user_id": uid, "aws_profile": "", "github_repo": "", "workflow_path": ""}
    return {
        "user_id": uid,
        "aws_profile": str(raw.get("aws_profile") or "").strip(),
        "github_repo": str(raw.get("github_repo") or "").strip(),
        "workflow_path": str(raw.get("workflow_path") or "").strip(),
    }


def save_deploy_credentials(
    user_id: str,
    *,
    aws_profile: str | None = None,
    github_repo: str | None = None,
    workflow_path: str | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id required")
    root = repo_root or find_repo_root()
    current = load_deploy_credentials(uid, repo_root=root)
    if aws_profile is not None:
        current["aws_profile"] = str(aws_profile).strip()
    if github_repo is not None:
        current["github_repo"] = str(github_repo).strip()
    if workflow_path is not None:
        current["workflow_path"] = str(workflow_path).strip()
    path = _user_path(root, uid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "aws_profile": current["aws_profile"],
                "github_repo": current["github_repo"],
                "workflow_path": current["workflow_path"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return current
