from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def collab_policy_path(repo_root: Path) -> Path:
    return repo_root / "configs" / "collab_policy.yaml"


def load_collab_policy(repo_root: Path) -> dict[str, Any]:
    path = collab_policy_path(repo_root)
    if not path.is_file():
        return {
            "version": 1,
            "allow_external_collaborators": False,
            "max_session_participants": 20,
            "host_transfer_consent_hours": 24,
            "default_invite_role": "session_read",
            "write_may_start_runs": False,
        }
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {"version": 1}


def save_collab_policy(repo_root: Path, doc: dict[str, Any]) -> None:
    path = collab_policy_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(doc, sort_keys=False), encoding="utf-8")
