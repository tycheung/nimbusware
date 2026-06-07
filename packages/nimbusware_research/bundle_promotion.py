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
    rel = Path(".nimbusware") / "research" / "catalog_candidates" / str(run_id)
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
    base = repo_root / ".nimbusware" / "research" / "catalog_candidates"
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


def load_catalog_candidate(
    repo_root: Path,
    *,
    run_id: str,
    candidate_id: str,
) -> dict[str, Any]:
    path = (
        repo_root
        / ".nimbusware"
        / "research"
        / "catalog_candidates"
        / run_id.strip()
        / f"{candidate_id.strip()}.json"
    )
    if not path.is_file():
        msg = f"catalog candidate not found: {run_id}/{candidate_id}"
        raise FileNotFoundError(msg)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "catalog candidate must be a JSON object"
        raise ValueError(msg)
    return payload


def candidate_to_bundle_entry(candidate: dict[str, Any]) -> dict[str, Any]:
    bundle_id = str(
        candidate.get("bundle_id")
        or candidate.get("candidate_id")
        or candidate.get("pattern_id")
        or "",
    ).strip()
    if not bundle_id:
        msg = "catalog candidate missing bundle_id or candidate_id"
        raise ValueError(msg)
    title = candidate.get("title") or candidate.get("summary") or bundle_id
    tags_raw = candidate.get("tags") or candidate.get("bundle_tags") or []
    tags = [str(t) for t in tags_raw if t is not None] if isinstance(tags_raw, list) else []
    return {"id": bundle_id, "title": str(title), "tags": tags}


def write_stitch_catalog_candidate(
    repo_root: Path,
    *,
    run_id: UUID,
    manifest_id: str,
    files_added: list[str],
    bundle_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a catalog candidate after successful stitch apply for integrator review."""
    hints = dict(bundle_hints or {})
    candidate_id = str(
        hints.pop("candidate_id", None) or f"stitch-{manifest_id.replace('-', '')[:12]}"
    ).strip()
    title = hints.pop("title", None) or f"Stitch transplant {manifest_id[:8]}"
    tags_raw = hints.pop("tags", None) or ["stitch", "transplant"]
    tags = [str(t) for t in tags_raw if t is not None] if isinstance(tags_raw, list) else []
    return write_catalog_candidate(
        repo_root,
        run_id=run_id,
        candidate_id=candidate_id,
        bundle_hints={
            "title": title,
            "tags": tags,
            "source": "stitch_applied",
            "manifest_id": manifest_id,
            "files_added": list(files_added),
            **hints,
        },
    )


def mark_catalog_candidate_promoted(
    repo_root: Path,
    *,
    run_id: str,
    candidate_id: str,
) -> None:
    path = (
        repo_root
        / ".nimbusware"
        / "research"
        / "catalog_candidates"
        / run_id.strip()
        / f"{candidate_id.strip()}.json"
    )
    if not path.is_file():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(payload, dict):
        payload["status"] = "promoted"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
