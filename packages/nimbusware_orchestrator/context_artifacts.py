from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5


@dataclass(frozen=True)
class ContextArtifactRecord:
    artifact_id: str
    project_id: str
    title: str
    content: str
    kind: str
    created_at: str
    owner_user_id: str = ""
    visibility: str = "private"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


_MEMORY: dict[str, list[ContextArtifactRecord]] = {}


def _repo_root() -> Path:
    from nimbusware_env import find_repo_root

    return find_repo_root()


def _artifacts_dir(project_id: str) -> Path:
    return _repo_root() / ".cache" / "nimbusware" / "context-artifacts" / project_id


def _persist_record(record: ContextArtifactRecord) -> None:
    root = _artifacts_dir(record.project_id)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{record.artifact_id}.json"
    path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")


def _load_project_from_disk(project_id: str) -> list[ContextArtifactRecord]:
    root = _artifacts_dir(project_id)
    if not root.is_dir():
        return []
    rows: list[ContextArtifactRecord] = []
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        try:
            rows.append(
                ContextArtifactRecord(
                    artifact_id=str(data["artifact_id"]),
                    project_id=str(data["project_id"]),
                    title=str(data.get("title") or ""),
                    content=str(data.get("content") or ""),
                    kind=str(data.get("kind") or "note"),
                    created_at=str(data.get("created_at") or ""),
                    owner_user_id=str(data.get("owner_user_id") or ""),
                    visibility=str(data.get("visibility") or "private"),
                ),
            )
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def _merge_memory_and_disk(project_id: str) -> list[ContextArtifactRecord]:
    pid = project_id.strip()
    disk = {r.artifact_id: r for r in _load_project_from_disk(pid)}
    for row in _MEMORY.get(pid, []):
        disk[row.artifact_id] = row
    return sorted(disk.values(), key=lambda r: r.created_at)


def create_context_artifact(
    *,
    project_id: UUID | str,
    title: str,
    content: str,
    kind: str = "note",
    owner_user_id: str = "",
    visibility: str = "private",
) -> ContextArtifactRecord:
    pid = str(project_id).strip()
    title_n = title.strip()
    if not title_n:
        raise ValueError("title required")
    content_n = content.strip()
    if not content_n:
        raise ValueError("content required")
    kind_n = (kind or "note").strip() or "note"
    record = ContextArtifactRecord(
        artifact_id=str(uuid4()),
        project_id=pid,
        title=title_n,
        content=content_n,
        kind=kind_n,
        created_at=datetime.now(timezone.utc).isoformat(),
        owner_user_id=owner_user_id.strip(),
        visibility=(visibility or "private").strip() or "private",
    )
    bucket = _MEMORY.setdefault(pid, [])
    bucket.append(record)
    _persist_record(record)
    return record


def list_context_artifacts(project_id: UUID | str) -> list[ContextArtifactRecord]:
    return _merge_memory_and_disk(str(project_id).strip())


def list_context_artifacts_for_actor(
    project_id: UUID | str,
    actor_user_id: str,
) -> list[ContextArtifactRecord]:
    actor = actor_user_id.strip()
    rows = list_context_artifacts(project_id)
    if not actor:
        return [r for r in rows if r.visibility in ("project", "shared")]
    visible: list[ContextArtifactRecord] = []
    for row in rows:
        if row.visibility in ("project", "shared"):
            visible.append(row)
        elif row.owner_user_id == actor or not row.owner_user_id:
            visible.append(row)
    return visible


def get_context_artifact(project_id: UUID | str, artifact_id: str) -> ContextArtifactRecord | None:
    pid = str(project_id).strip()
    target = artifact_id.strip()
    for row in _merge_memory_and_disk(pid):
        if row.artifact_id == target:
            return row
    return None


def latest_compaction_summary_from_events(rows: list[dict[str, Any]]) -> str | None:
    from nimbusware_projections.builders.context_budget import _latest_compaction_row

    row = _latest_compaction_row(rows)
    if row is None:
        return None
    meta = row.get("metadata")
    if not isinstance(meta, dict):
        return None
    summary = meta.get("summary")
    return str(summary).strip() if isinstance(summary, str) and summary.strip() else None


def create_context_artifact_from_compaction(
    *,
    project_id: UUID | str,
    rows: list[dict[str, Any]],
    title: str | None = None,
) -> ContextArtifactRecord:
    summary = latest_compaction_summary_from_events(rows)
    if not summary:
        raise ValueError("no compaction summary on run timeline")
    last = None
    from nimbusware_projections.builders.context_budget import estimate_context_budget

    budget = estimate_context_budget(rows)
    last = budget.get("last_compaction")
    cid = ""
    if isinstance(last, dict):
        cid = str(last.get("compaction_id") or "").strip()
    auto_title = (
        title.strip()
        if title and title.strip()
        else (f"Compaction {cid[:8]}" if cid else "Compacted context")
    )
    return create_context_artifact(
        project_id=project_id,
        title=auto_title,
        content=summary,
        kind="compaction",
    )


def insert_context_artifact_into_run(
    store: object,
    *,
    run_id: object,
    artifact: ContextArtifactRecord,
) -> dict[str, Any]:
    from datetime import datetime, timezone
    from uuid import uuid4

    from agent_core.models import EventType, StageStartedEvent, StageStartedPayload

    store.append(  # type: ignore[attr-defined]
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,  # type: ignore[arg-type]
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "artifact_id": artifact.artifact_id,
                "project_id": artifact.project_id,
                "title": artifact.title,
                "content": artifact.content[:8000],
                "kind": artifact.kind,
            },
            payload=StageStartedPayload(
                stage_name="campaign.context.artifact.inserted",
                attempt=1,
            ),
        ),
    )
    return {
        "artifact_id": artifact.artifact_id,
        "title": artifact.title,
        "kind": artifact.kind,
    }


def bridge_artifact_to_memory_index(
    artifact: ContextArtifactRecord,
    *,
    repo_root: Path | None = None,
) -> dict[str, str]:
    from nimbusware_env import find_repo_root

    root = repo_root or find_repo_root()
    bridge_dir = root / ".cache" / "nimbusware" / "memory-bridge" / artifact.project_id
    bridge_dir.mkdir(parents=True, exist_ok=True)
    path = bridge_dir / f"{artifact.artifact_id}.json"
    payload = {
        "artifact_id": artifact.artifact_id,
        "project_id": artifact.project_id,
        "title": artifact.title,
        "excerpt": artifact.content[:4000],
        "kind": artifact.kind,
        "source": "context_artifact",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    result: dict[str, Any] = {"bridge_path": str(path), "artifact_id": artifact.artifact_id}
    rebuild = maybe_rebuild_memory_faiss_from_bridges(artifact.project_id, repo_root=root)
    if rebuild is not None:
        result["faiss_rebuild"] = rebuild
    return result


def maybe_rebuild_memory_faiss_from_bridges(
    project_id: str,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any] | None:
    from nimbusware_env.env_flags import env_truthy

    if not env_truthy("NIMBUSWARE_CONTEXT_ARTIFACT_FAISS_REBUILD"):
        return None

    from nimbusware_env import find_repo_root
    from nimbusware_memory.embeddings import embed_text, embedding_model_id_for_mode
    from nimbusware_memory.faiss_index import build_memory_faiss_index
    from nimbusware_memory.manifest import (
        MemoryIndexManifest,
        default_memory_index_dir,
        write_manifest,
    )
    from nimbusware_memory.models import MemoryChunkRecord

    root = repo_root or find_repo_root()
    bridge_dir = root / ".cache" / "nimbusware" / "memory-bridge" / project_id
    if not bridge_dir.is_dir():
        return {"rebuilt": False, "reason": "no_bridge_dir"}

    records: list[MemoryChunkRecord] = []
    generation_id = uuid4()
    scope = f"bridge:{project_id}"
    model_id = embedding_model_id_for_mode("deterministic")
    for sidecar in sorted(bridge_dir.glob("*.json")):
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        excerpt = str(payload.get("excerpt") or payload.get("title") or "").strip()
        if not excerpt:
            continue
        vec = embed_text(excerpt, mode="deterministic")
        artifact_id = str(payload.get("artifact_id") or sidecar.stem)
        records.append(
            MemoryChunkRecord(
                chunk_id=uuid5(NAMESPACE_URL, f"{scope}|{artifact_id}|{excerpt[:200]}"),
                generation_id=generation_id,
                repo_scope_hash=scope,
                run_id=uuid4(),
                source_event_type="context_artifact.bridge",
                source_store_seq=None,
                finding_id=None,
                category="context_artifact",
                severity="info",
                excerpt=excerpt[:4000],
                embedding_model_id=model_id,
                embedding_dim=len(vec),
                embedding_vector=vec,
            ),
        )

    if not records:
        return {"rebuilt": False, "reason": "no_bridge_records"}

    index_dir = default_memory_index_dir(root)
    manifest = MemoryIndexManifest(
        generation_id=str(generation_id),
        repo_scope_hash=scope,
        embedding_mode="deterministic",
        embedding_model_id=model_id,
        chunk_count=len(records),
        built_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    write_manifest(index_dir, manifest)
    build_memory_faiss_index(chunks=records, index_dir=index_dir)
    return {"rebuilt": True, "chunk_count": len(records), "index_dir": str(index_dir)}


def clear_context_artifacts_memory() -> None:
    _MEMORY.clear()
