from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

from nimbusware_env.env_flags import nimbusware_memory_index_dir
from nimbusware_memory.models import EmbeddingMode


class MemoryIndexManifest(BaseModel):
    schema_version: int = 1
    generation_id: str
    repo_scope_hash: str
    org_scope_hash: str | None = None
    tenant_id: str | None = None
    embedding_mode: EmbeddingMode
    embedding_model_id: str
    chunk_count: int = Field(ge=0)
    built_at: str


def default_memory_index_dir(repo_root: Path) -> Path:
    env = nimbusware_memory_index_dir()
    if env:
        return Path(env).resolve()
    return (repo_root / "configs" / "memory" / "index").resolve()


def write_manifest(index_dir: Path, manifest: MemoryIndexManifest) -> Path:
    index_dir.mkdir(parents=True, exist_ok=True)
    path = index_dir / "manifest.json"
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def read_manifest(index_dir: Path) -> MemoryIndexManifest | None:
    path = index_dir / "manifest.json"
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return MemoryIndexManifest.model_validate(raw)


def latest_generation_id(index_dir: Path) -> UUID | None:
    manifest = read_manifest(index_dir)
    if manifest is None:
        return None
    try:
        return UUID(manifest.generation_id)
    except ValueError:
        return None
