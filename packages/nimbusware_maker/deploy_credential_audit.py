from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from nimbusware_env import find_repo_root


def _audit_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / ".nimbusware" / "platform" / "deploy_audit.jsonl"


def _user_ref(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return digest[:16]


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
