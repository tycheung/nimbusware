from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from research.models import ResearchBrief


def research_artifacts_dir(repo_root: Path) -> Path:
    return repo_root / ".nimbusware" / "research" / "briefs"


def persist_research_brief(repo_root: Path, brief: ResearchBrief) -> Path:
    root = research_artifacts_dir(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    artifact_id = brief.artifact_id or str(uuid4())
    path = root / f"{artifact_id}.json"
    payload = brief.model_copy(update={"artifact_id": artifact_id})
    path.write_text(
        json.dumps(payload.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return path


def read_research_brief(repo_root: Path, artifact_id: str) -> ResearchBrief | None:
    path = research_artifacts_dir(repo_root) / f"{artifact_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return ResearchBrief.model_validate(data)
