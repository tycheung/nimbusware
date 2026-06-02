"""Memory index sync and stale detection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from hermes_memory.faiss_index import memory_faiss_index_ready
from hermes_memory.manifest import default_memory_index_dir, read_manifest


def memory_index_sync_state(repo_root: Path) -> dict[str, Any]:
    """Compare on-disk manifest/FAISS mtimes for operator hints (mirrors bundle sync)."""
    index_dir = default_memory_index_dir(repo_root)
    manifest_path = index_dir / "manifest.json"
    faiss_path = index_dir / "faiss.index"
    order_path = index_dir / "chunk_order.json"
    ready = memory_faiss_index_ready(index_dir)
    out: dict[str, Any] = {
        "index_dir": str(index_dir),
        "manifest_exists": manifest_path.is_file(),
        "faiss_ready": ready,
        "generation_id": None,
        "stale": None,
    }
    manifest = read_manifest(index_dir)
    if manifest is not None:
        out["generation_id"] = manifest.generation_id
    if not manifest_path.is_file():
        out["stale"] = None
        return out
    manifest_mtime = int(manifest_path.stat().st_mtime_ns)
    out["manifest_mtime_ns"] = manifest_mtime
    if not ready:
        out["stale"] = True
        return out
    idx_mtime = max(int(faiss_path.stat().st_mtime_ns), int(order_path.stat().st_mtime_ns))
    out["index_max_mtime_ns"] = idx_mtime
    out["stale"] = manifest_mtime > idx_mtime
    return out


def memory_sync_manifest_stub(repo_root: Path) -> dict[str, Any]:
    """Read-only sync manifest shape for remote hydrate."""
    from hermes_memory.org_scope import fleet_memory_enabled

    index_dir = default_memory_index_dir(repo_root)
    manifest = read_manifest(index_dir)
    sync_path = index_dir / "sync_manifest.json"
    if sync_path.is_file():
        return cast(dict[str, Any], json.loads(sync_path.read_text(encoding="utf-8")))
    state = memory_index_sync_state(repo_root)
    remote_sync = "not_configured"
    if fleet_memory_enabled():
        try:
            from hermes_memory.remote_store import resolve_canonical_store_root

            resolve_canonical_store_root()
            remote_sync = "configured"
        except ValueError:
            remote_sync = "not_configured"
    return {
        "schema_version": 1,
        "repo_scope_hash": manifest.repo_scope_hash if manifest else None,
        "org_scope_hash": manifest.org_scope_hash if manifest else None,
        "generation_id": manifest.generation_id if manifest else state.get("generation_id"),
        "faiss_ready": state.get("faiss_ready"),
        "remote_sync": remote_sync,
    }
