"""Code Researcher → catalog candidate promotion path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID


def write_catalog_candidate(
    repo_root: Path,
    *,
    run_id: UUID,
    candidate_id: str,
    bundle_hints: dict[str, Any],
) -> dict[str, Any]:
    rel = Path(".hermes") / "research" / "catalog_candidates" / str(run_id)
    abs_dir = repo_root / rel
    abs_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": str(run_id),
        "candidate_id": candidate_id,
        "status": "pending_integrator_review",
        **bundle_hints,
    }
    out = abs_dir / f"{candidate_id}.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {
        "catalog_candidate_path": str(rel / f"{candidate_id}.json").replace("\\", "/"),
        "candidate_id": candidate_id,
    }


def list_catalog_candidates(repo_root: Path, *, limit: int = 100) -> list[dict[str, Any]]:
    base = repo_root / ".hermes" / "research" / "catalog_candidates"
    if not base.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for run_dir in sorted(base.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        for path in sorted(run_dir.glob("*.json"), reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                payload.setdefault("run_id", run_dir.name)
                rows.append(payload)
            if len(rows) >= limit:
                return rows
    return rows
