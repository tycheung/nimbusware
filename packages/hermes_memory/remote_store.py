"""Remote canonical fleet memory store adapter."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hermes_memory.models import EmbeddingMode, MemoryChunkRecord


@dataclass(frozen=True)
class FleetMemoryBundle:
    schema_version: int
    tenant_id: str
    org_scope_hash: str
    generation_id: str
    repo_scope_hash: str | None
    embedding_mode: EmbeddingMode
    embedding_model_id: str
    chunk_count: int
    built_at: str
    chunks: tuple[MemoryChunkRecord, ...]


def resolve_canonical_store_root(explicit: Path | str | None = None) -> Path:
    if explicit is not None:
        return Path(explicit).resolve()
    env = os.environ.get("NIMBUSWARE_FLEET_MEMORY_STORE_URI", "").strip()
    if env.startswith("file://"):
        return Path(env.removeprefix("file://")).resolve()
    if env:
        return Path(env).resolve()
    fallback = os.environ.get("NIMBUSWARE_FLEET_MEMORY_STORE_DIR", "").strip()
    if fallback:
        return Path(fallback).resolve()
    msg = (
        "Fleet memory canonical store not configured "
        "(set NIMBUSWARE_FLEET_MEMORY_STORE_URI or NIMBUSWARE_FLEET_MEMORY_STORE_DIR)"
    )
    raise ValueError(msg)


class FileFleetMemoryCanonicalStore:
    """File-backed canonical store: ``{root}/{org_scope_hash}/{generation_id}/``."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def push(self, bundle: FleetMemoryBundle) -> Path:
        dest = self.root / bundle.org_scope_hash / bundle.generation_id
        dest.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": bundle.schema_version,
            "tenant_id": bundle.tenant_id,
            "org_scope_hash": bundle.org_scope_hash,
            "generation_id": bundle.generation_id,
            "repo_scope_hash": bundle.repo_scope_hash,
            "embedding_mode": bundle.embedding_mode,
            "embedding_model_id": bundle.embedding_model_id,
            "chunk_count": bundle.chunk_count,
            "built_at": bundle.built_at,
        }
        (dest / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        chunks_payload = [c.model_dump(mode="json") for c in bundle.chunks]
        (dest / "chunks.json").write_text(
            json.dumps(chunks_payload, indent=2) + "\n",
            encoding="utf-8",
        )
        latest = self.root / bundle.org_scope_hash / "LATEST"
        latest.write_text(bundle.generation_id + "\n", encoding="utf-8")
        return dest

    def pull_latest(self, org_scope_hash: str) -> FleetMemoryBundle | None:
        scope_dir = self.root / org_scope_hash
        latest_path = scope_dir / "LATEST"
        if not latest_path.is_file():
            gens = (
                sorted(p.name for p in scope_dir.iterdir() if p.is_dir())
                if scope_dir.is_dir()
                else []
            )
            if not gens:
                return None
            generation_id = gens[-1]
        else:
            generation_id = latest_path.read_text(encoding="utf-8").strip()
        return self.pull_generation(org_scope_hash, generation_id)

    def pull_generation(self, org_scope_hash: str, generation_id: str) -> FleetMemoryBundle | None:
        dest = self.root / org_scope_hash / generation_id
        manifest_path = dest / "manifest.json"
        chunks_path = dest / "chunks.json"
        if not manifest_path.is_file() or not chunks_path.is_file():
            return None
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        chunks = tuple(MemoryChunkRecord.model_validate(c) for c in raw_chunks)
        return FleetMemoryBundle(
            schema_version=int(manifest.get("schema_version", 1)),
            tenant_id=str(manifest["tenant_id"]),
            org_scope_hash=str(manifest["org_scope_hash"]),
            generation_id=str(manifest["generation_id"]),
            repo_scope_hash=manifest.get("repo_scope_hash"),
            embedding_mode=str(manifest["embedding_mode"]),  # type: ignore[arg-type]
            embedding_model_id=str(manifest["embedding_model_id"]),
            chunk_count=int(manifest.get("chunk_count", len(chunks))),
            built_at=str(manifest.get("built_at") or _utc_now()),
            chunks=chunks,
        )

    def list_generations(self, org_scope_hash: str) -> list[str]:
        scope_dir = self.root / org_scope_hash
        if not scope_dir.is_dir():
            return []
        return sorted(p.name for p in scope_dir.iterdir() if p.is_dir() and p.name != "LATEST")


def bundle_from_store_rows(
    *,
    tenant_id: UUID,
    org_scope_hash: str,
    generation_id: UUID,
    repo_scope_hash: str | None,
    embedding_mode: EmbeddingMode,
    embedding_model_id: str,
    chunks: list[MemoryChunkRecord],
) -> FleetMemoryBundle:
    return FleetMemoryBundle(
        schema_version=1,
        tenant_id=str(tenant_id),
        org_scope_hash=org_scope_hash,
        generation_id=str(generation_id),
        repo_scope_hash=repo_scope_hash,
        embedding_mode=embedding_mode,
        embedding_model_id=embedding_model_id,
        chunk_count=len(chunks),
        built_at=_utc_now(),
        chunks=tuple(chunks),
    )


def import_bundle_to_memory_store(
    memory_store: Any,
    bundle: FleetMemoryBundle,
    *,
    tenant_id: UUID,
    manifest_relpath: str | None = None,
) -> Any:
    return memory_store.replace_generation(
        generation_id=UUID(bundle.generation_id),
        tenant_id=tenant_id,
        org_scope_hash=bundle.org_scope_hash,
        repo_scope_hash=bundle.repo_scope_hash or bundle.org_scope_hash,
        embedding_mode=bundle.embedding_mode,
        embedding_model_id=bundle.embedding_model_id,
        chunks=list(bundle.chunks),
        manifest_relpath=manifest_relpath,
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
