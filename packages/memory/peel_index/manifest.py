from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from env.env_flags import env_str


@dataclass(frozen=True)
class MemoryIndexManifest:
    generation_id: str
    repo_scope_hash: str
    embedding_mode: str
    embedding_model_id: str
    chunk_count: int
    built_at: str
    org_scope_hash: str | None = None


def default_memory_index_dir(repo_root: Path) -> Path:
    explicit = env_str("NIMBUSWARE_MEMORY_INDEX_DIR")
    if explicit:
        return Path(explicit).resolve()
    return (repo_root / ".cache" / "nimbusware" / "memory-index").resolve()


def read_manifest(index_dir: Path) -> MemoryIndexManifest | None:
    path = index_dir / "manifest.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    try:
        return MemoryIndexManifest(
            generation_id=str(raw["generation_id"]),
            repo_scope_hash=str(raw["repo_scope_hash"]),
            embedding_mode=str(raw.get("embedding_mode") or "deterministic"),
            embedding_model_id=str(raw.get("embedding_model_id") or ""),
            chunk_count=int(raw.get("chunk_count") or 0),
            built_at=str(raw.get("built_at") or ""),
            org_scope_hash=str(raw["org_scope_hash"]) if raw.get("org_scope_hash") else None,
        )
    except (KeyError, TypeError, ValueError):
        return None


def write_manifest(index_dir: Path, manifest: MemoryIndexManifest) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    path = index_dir / "manifest.json"
    path.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")


def latest_generation_id(index_dir: Path) -> str | None:
    manifest = read_manifest(index_dir)
    return manifest.generation_id if manifest is not None else None
