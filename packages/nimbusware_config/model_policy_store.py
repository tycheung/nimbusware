from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def model_policy_path(repo_root: Path) -> Path:
    return repo_root / "configs" / "model_policy.yaml"


def load_model_policy(repo_root: Path) -> dict[str, Any]:
    path = model_policy_path(repo_root)
    if not path.is_file():
        return {
            "version": 1,
            "allowed_cloud_providers": [],
            "require_admin_for_cloud_swap": False,
            "blocked_model_ids": [],
            "audit_include_binding_events": True,
        }
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {"version": 1}


def save_model_policy(repo_root: Path, doc: dict[str, Any]) -> None:
    path = model_policy_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")


def policy_allows_cloud_provider(policy: dict[str, Any], provider_id: str) -> bool:
    raw = policy.get("allowed_cloud_providers")
    if not isinstance(raw, list) or not raw:
        return True
    allowed = {str(p).lower() for p in raw}
    return provider_id.strip().lower() in allowed


def policy_allows_model(policy: dict[str, Any], model_id: str) -> bool:
    raw = policy.get("blocked_model_ids")
    if not isinstance(raw, list) or not raw:
        return True
    blocked = {str(m) for m in raw}
    return model_id.strip() not in blocked
