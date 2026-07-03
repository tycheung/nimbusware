from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def model_policy_path(repo_root: Path) -> Path:
    return repo_root / "configs" / "model_policy.yaml"


def load_model_policy(repo_root: Path) -> dict[str, Any]:
    from config.model_routing_sections import load_model_policy_doc

    return load_model_policy_doc(repo_root)


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
