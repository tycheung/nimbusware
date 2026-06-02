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
