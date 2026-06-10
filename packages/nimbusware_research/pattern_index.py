from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict
from uuid import uuid4

from nimbusware_memory.repo_scope import repo_scope_hash


class PatternIndexRecord(TypedDict):
    pattern_id: str
    repo_url: str
    paths: list[str]
    license: str
    embedding_ref: str


def pattern_index_path(repo_root: Path) -> Path:
    scope = repo_scope_hash(repo_root)
    return repo_root / ".nimbusware" / "research" / "patterns" / f"{scope}.json"


def append_pattern_index(
    repo_root: Path,
    *,
    pattern_id: str,
    repo_url: str,
    paths: list[str],
    license_name: str,
    embedding_ref: str,
) -> PatternIndexRecord:
    path = pattern_index_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                entries = [e for e in loaded if isinstance(e, dict)]
        except (OSError, json.JSONDecodeError):
            entries = []
    entry: dict[str, object] = {
        "pattern_id": pattern_id,
        "repo_url": repo_url,
        "paths": list(paths),
        "license": license_name,
        "embedding_ref": embedding_ref,
    }
    entries.append(entry)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return PatternIndexRecord(
        pattern_id=pattern_id,
        repo_url=repo_url,
        paths=paths,
        license=license_name,
        embedding_ref=embedding_ref,
    )


def new_pattern_id() -> str:
    return str(uuid4())
