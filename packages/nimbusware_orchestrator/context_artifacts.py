"""Project-scoped context artifacts (in-memory + optional file cache)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ContextArtifactRecord:
    artifact_id: str
    project_id: str
    title: str
    content: str
    kind: str
    created_at: str

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
    )
    bucket = _MEMORY.setdefault(pid, [])
    bucket.append(record)
    _persist_record(record)
    return record


def list_context_artifacts(project_id: UUID | str) -> list[ContextArtifactRecord]:
    return _merge_memory_and_disk(str(project_id).strip())


def get_context_artifact(project_id: UUID | str, artifact_id: str) -> ContextArtifactRecord | None:
    pid = str(project_id).strip()
    target = artifact_id.strip()
    for row in _merge_memory_and_disk(pid):
        if row.artifact_id == target:
            return row
    return None


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


def clear_context_artifacts_memory() -> None:
    """Test helper: reset in-memory artifact index."""
    _MEMORY.clear()
