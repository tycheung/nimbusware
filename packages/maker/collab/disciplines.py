from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from env import find_repo_root

_MENTION_RE = re.compile(r"@([a-zA-Z][\w-]*)")


@lru_cache(maxsize=4)
def _load_catalog(repo_root: str) -> dict[str, dict[str, Any]]:
    path = Path(repo_root) / "configs" / "collab" / "disciplines.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    items = raw.get("disciplines")
    if not isinstance(items, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in items:
        if not isinstance(row, dict):
            continue
        did = str(row.get("id") or "").strip().lower()
        if not did:
            continue
        out[did] = row
    return out


def _alias_map(catalog: dict[str, dict[str, Any]]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for did, row in catalog.items():
        for alias in row.get("aliases") or []:
            key = str(alias).strip().lower()
            if key:
                aliases[key] = did
    return aliases


def list_disciplines(*, repo_root: Path | None = None) -> list[dict[str, Any]]:
    root = repo_root or find_repo_root()
    catalog = _load_catalog(str(root))
    out: list[dict[str, Any]] = []
    for did in sorted(catalog):
        row = catalog[did]
        entry: dict[str, Any] = {
            "id": did,
            "display_name": str(row.get("display_name") or did),
            "taxonomy_key": str(row.get("taxonomy_key") or "").strip() or None,
            "aliases": [str(a) for a in (row.get("aliases") or []) if str(a).strip()],
        }
        keys = row.get("taxonomy_keys")
        if isinstance(keys, list) and keys:
            entry["taxonomy_keys"] = [str(k) for k in keys if str(k).strip()]
        out.append(entry)
    return out


def normalize_discipline(raw: str, *, repo_root: Path | None = None) -> str | None:
    key = str(raw or "").strip().lower().lstrip("@")
    if not key:
        return None
    root = repo_root or find_repo_root()
    catalog = _load_catalog(str(root))
    if key in catalog:
        return key
    return _alias_map(catalog).get(key)


def taxonomy_keys_for_discipline(
    discipline: str,
    *,
    repo_root: Path | None = None,
) -> tuple[str, ...]:
    root = repo_root or find_repo_root()
    catalog = _load_catalog(str(root))
    row = catalog.get(discipline)
    if not row:
        return ()
    keys = row.get("taxonomy_keys")
    if isinstance(keys, list) and keys:
        return tuple(str(k).strip() for k in keys if str(k).strip())
    single = str(row.get("taxonomy_key") or "").strip()
    return (single,) if single else ()


def parse_discipline_mentions(message: str, *, repo_root: Path | None = None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _MENTION_RE.findall(str(message or "")):
        discipline = normalize_discipline(match, repo_root=repo_root)
        if discipline and discipline not in seen:
            seen.add(discipline)
            out.append(discipline)
    return out


def discipline_routes(
    message: str,
    *,
    participant_discipline: str | None = None,
    solo_hat: str | None = None,
    repo_root: Path | None = None,
) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for discipline in parse_discipline_mentions(message, repo_root=repo_root):
        for taxonomy_key in taxonomy_keys_for_discipline(discipline, repo_root=repo_root):
            routes.append(
                {
                    "discipline": discipline,
                    "taxonomy_key": taxonomy_key,
                    "source": "mention",
                },
            )
    if routes:
        return routes
    hat = normalize_discipline(participant_discipline or "", repo_root=repo_root)
    if not hat:
        hat = normalize_discipline(solo_hat or "", repo_root=repo_root)
    if not hat:
        return []
    for taxonomy_key in taxonomy_keys_for_discipline(hat, repo_root=repo_root):
        routes.append(
            {
                "discipline": hat,
                "taxonomy_key": taxonomy_key,
                "source": "participant_hat" if participant_discipline else "solo_hat",
            },
        )
    return routes
