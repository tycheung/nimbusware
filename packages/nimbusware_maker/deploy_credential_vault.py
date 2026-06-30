from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root
from nimbusware_maker.deploy_target_enforcement import (
    DEFAULT_DEPLOY_ENVIRONMENT,
    normalize_deploy_environment,
)


def _user_path(repo_root: Path, user_id: str) -> Path:
    return repo_root / "configs" / "deploy" / "users" / f"{user_id.strip()}.yaml"


def load_deploy_credentials(
    user_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        return {
            "user_id": "",
            "aws_profile": "",
            "github_repo": "",
            "workflow_path": "",
            "deploy_environment": DEFAULT_DEPLOY_ENVIRONMENT,
        }
    root = repo_root or find_repo_root()
    path = _user_path(root, uid)
    if not path.is_file():
        return {
            "user_id": uid,
            "aws_profile": "",
            "github_repo": "",
            "workflow_path": "",
            "deploy_environment": DEFAULT_DEPLOY_ENVIRONMENT,
        }
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {
            "user_id": uid,
            "aws_profile": "",
            "github_repo": "",
            "workflow_path": "",
            "deploy_environment": DEFAULT_DEPLOY_ENVIRONMENT,
        }
    return {
        "user_id": uid,
        "aws_profile": str(raw.get("aws_profile") or "").strip(),
        "github_repo": str(raw.get("github_repo") or "").strip(),
        "workflow_path": str(raw.get("workflow_path") or "").strip(),
        "deploy_environment": normalize_deploy_environment(
            str(raw.get("deploy_environment") or DEFAULT_DEPLOY_ENVIRONMENT)
        ),
    }


def save_deploy_credentials(
    user_id: str,
    *,
    aws_profile: str | None = None,
    github_repo: str | None = None,
    workflow_path: str | None = None,
    deploy_environment: str | None = None,
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
    if deploy_environment is not None:
        current["deploy_environment"] = normalize_deploy_environment(deploy_environment)
    path = _user_path(root, uid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "aws_profile": current["aws_profile"],
                "github_repo": current["github_repo"],
                "workflow_path": current["workflow_path"],
                "deploy_environment": current["deploy_environment"],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return current


def _audit_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / ".nimbusware" / "platform" / "deploy_audit.jsonl"


def _user_ref(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return digest[:16]


def list_deploy_audit_events(
    *,
    run_id: str = "",
    limit: int = 50,
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    path = _audit_path(repo_root)
    if not path.is_file():
        return []
    cap = max(1, min(200, int(limit)))
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if run_id and str(row.get("run_id") or "") != run_id:
            continue
        rows.append(row)
    if len(rows) > cap:
        rows = rows[-cap:]
    return rows


def append_deploy_audit_event(
    event: str,
    *,
    user_id: str = "",
    run_id: str = "",
    tenant_slug: str = "",
    deploy_target: str = "",
    scopes: list[str] | None = None,
    detail: str = "",
    repo_root: Path | None = None,
) -> None:
    path = _audit_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "event": event,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "user_ref": _user_ref(user_id) if user_id else "",
        "run_id": run_id,
        "tenant_slug": tenant_slug,
        "deploy_target": deploy_target,
        "scopes": scopes or [],
        "detail": detail[:500],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def audit_credentials_updated(
    *,
    user_id: str,
    tenant_slug: str | None = None,
    scopes: list[str] | None = None,
    deploy_target: str | None = None,
    repo_root: Path | None = None,
) -> None:
    append_deploy_audit_event(
        "deploy.credentials.updated",
        user_id=user_id,
        tenant_slug=tenant_slug or "",
        deploy_target=deploy_target or "",
        scopes=scopes,
        repo_root=repo_root,
    )


def audit_credentials_used(
    *,
    user_id: str,
    run_id: str,
    action: str,
    tenant_slug: str | None = None,
    deploy_target: str | None = None,
    scopes: list[str] | None = None,
    repo_root: Path | None = None,
) -> None:
    append_deploy_audit_event(
        f"deploy.{action}",
        user_id=user_id,
        run_id=run_id,
        tenant_slug=tenant_slug or "",
        deploy_target=deploy_target or "",
        scopes=scopes,
        repo_root=repo_root,
    )
