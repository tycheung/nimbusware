from __future__ import annotations

import json
from pathlib import Path

from research.stitch_models import TransplantManifest


def stitch_manifests_dir(repo_root: Path) -> Path:
    return repo_root / ".nimbusware" / "stitch" / "manifests"


def persist_transplant_manifest(repo_root: Path, manifest: TransplantManifest) -> Path:
    root = stitch_manifests_dir(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{manifest.manifest_id}.json"
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return path


def read_transplant_manifest(repo_root: Path, manifest_id: str) -> TransplantManifest | None:
    path = stitch_manifests_dir(repo_root) / f"{manifest_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return TransplantManifest.model_validate(data)
