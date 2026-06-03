from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_model_catalog(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / "configs" / "hardware" / "model_catalog.json"
    if not path.is_file():
        return []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(doc, dict):
        return []
    models = doc.get("models")
    return [m for m in models if isinstance(m, dict)] if isinstance(models, list) else []
