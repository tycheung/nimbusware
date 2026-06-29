from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from nimbusware_env import find_repo_root

_FALLBACK: tuple[dict[str, Any], ...] = (
    {
        "id": "pair-devs-qa",
        "label": "2 devs + QA",
        "hint": "Invite frontend, backend, and QA reviewers",
        "disciplines": ["frontend", "backend", "qa"],
    },
    {
        "id": "full-team",
        "label": "Full team",
        "hint": "PM, architect, frontend, backend, and QA",
        "disciplines": ["pm", "architect", "frontend", "backend", "qa"],
    },
)


@lru_cache(maxsize=4)
def _load_catalog(repo_root: str) -> tuple[dict[str, Any], ...]:
    path = Path(repo_root) / "configs" / "collab" / "invite_templates.yaml"
    if not path.is_file():
        return _FALLBACK
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return _FALLBACK
    items = raw.get("templates")
    if not isinstance(items, list):
        return _FALLBACK
    out: list[dict[str, Any]] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        tid = str(row.get("id") or "").strip()
        if not tid:
            continue
        disciplines_raw = row.get("disciplines")
        disciplines = (
            [str(d).strip() for d in disciplines_raw if str(d).strip()]
            if isinstance(disciplines_raw, list)
            else []
        )
        out.append(
            {
                "id": tid,
                "label": str(row.get("label") or tid).strip(),
                "hint": str(row.get("hint") or "").strip(),
                "disciplines": disciplines,
            },
        )
    return tuple(out) if out else _FALLBACK


def list_invite_templates(*, repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = repo_root or find_repo_root()
    return [dict(row) for row in _load_catalog(str(root))]
