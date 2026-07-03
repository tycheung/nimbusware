from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from env import find_repo_root
from maker.collab.disciplines import (
    list_disciplines,
    normalize_discipline,
    taxonomy_keys_for_discipline,
)

COLLAB_AGENT_OVERLAY_UPDATED = "collab.agent_overlay.updated"


def _path(repo_root: Path, user_id: str) -> Path:
    return repo_root / "configs" / "collab" / "users" / f"{user_id.strip()}_agent_overlays.yaml"


def load_user_agent_overlays(
    user_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        return {"user_id": "", "overlays": {}}
    root = repo_root or find_repo_root()
    path = _path(root, uid)
    if not path.is_file():
        return {"user_id": uid, "overlays": {}}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {"user_id": uid, "overlays": {}}
    overlays = raw.get("overlays")
    if not isinstance(overlays, dict):
        overlays = {}
    cleaned: dict[str, Any] = {}
    for key, row in overlays.items():
        discipline = normalize_discipline(str(key), repo_root=root)
        if not discipline or not isinstance(row, dict):
            continue
        ext = str(row.get("prompt_extension") or "").strip()
        agent_id = str(row.get("custom_agent_id") or "").strip()
        if not ext and not agent_id:
            continue
        entry: dict[str, Any] = {}
        if ext:
            entry["prompt_extension"] = ext[:2000]
        if agent_id:
            entry["custom_agent_id"] = agent_id[:120]
        ver = row.get("version")
        if isinstance(ver, int) and ver > 0:
            entry["version"] = ver
        cleaned[discipline] = entry
    return {"user_id": uid, "overlays": cleaned}


def save_user_agent_overlay(
    user_id: str,
    discipline: str,
    *,
    custom_agent_id: str | None = None,
    prompt_extension: str | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id required")
    root = repo_root or find_repo_root()
    normalized = normalize_discipline(discipline, repo_root=root)
    if not normalized:
        raise ValueError("unknown discipline")
    body = load_user_agent_overlays(uid, repo_root=root)
    overlays = dict(body.get("overlays") or {})
    ext = str(prompt_extension or "").strip()
    agent_id = str(custom_agent_id or "").strip()
    if not ext and not agent_id:
        overlays.pop(normalized, None)
        version = 0
        cleared = True
    else:
        prev = overlays.get(normalized) or {}
        version = int(prev.get("version") or 0) + 1
        cleared = False
        row: dict[str, Any] = {"version": version}
        if ext:
            row["prompt_extension"] = ext[:2000]
        if agent_id:
            row["custom_agent_id"] = agent_id[:120]
        overlays[normalized] = row
    path = _path(root, uid)
    path.parent.mkdir(parents=True, exist_ok=True)
    if overlays:
        path.write_text(
            yaml.safe_dump({"overlays": overlays}, sort_keys=False),
            encoding="utf-8",
        )
    elif path.is_file():
        path.unlink()
    ap = root / ".nimbusware/platform/collab_audit.jsonl"
    ap.parent.mkdir(parents=True, exist_ok=True)
    ap.open("a", encoding="utf-8").write(
        json.dumps(
            {
                "event_type": COLLAB_AGENT_OVERLAY_UPDATED,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "user_id": uid,
                "discipline": normalized,
                "version": version,
                "cleared": cleared,
            },
            separators=(",", ":"),
        )
        + "\n"
    )
    return {"user_id": uid, "overlays": overlays}


def prompt_extension_for_taxonomy_key(
    user_id: str,
    taxonomy_key: str,
    *,
    repo_root: Path | None = None,
) -> str:
    uid = user_id.strip()
    role = str(taxonomy_key or "").strip()
    if not uid or not role:
        return ""
    root = repo_root or find_repo_root()
    overlays = load_user_agent_overlays(uid, repo_root=root).get("overlays") or {}
    for discipline in overlays:
        keys = taxonomy_keys_for_discipline(discipline, repo_root=root)
        if role in keys:
            ext = overlays[discipline].get("prompt_extension")
            return str(ext or "").strip()
    return ""


def prompt_addon_for_run_claims(
    claims: dict[str, str],
    *,
    repo_root: Path | None = None,
) -> str:
    root = repo_root or find_repo_root()
    parts: list[str] = []
    seen: set[str] = set()
    for role, claimer in claims.items():
        uid = str(claimer or "").strip()
        if not uid:
            continue
        ext = prompt_extension_for_taxonomy_key(uid, role, repo_root=root)
        if ext and ext not in seen:
            seen.add(ext)
            parts.append(ext)
    return "\n\n".join(parts)


def overlay_catalog(*, repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = repo_root or find_repo_root()
    return list_disciplines(repo_root=root)
