from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any


def load_persona_shelves_catalog(repo_root: Path) -> dict[str, Any]:
    from nimbusware_config.persist import load_persona_shelf
    from nimbusware_console.config_materializer import console_config_materializer

    mat = console_config_materializer(repo_root)
    shelf = load_persona_shelf(repo_root, materializer=mat)
    shelf.validate_structure()
    return shelf.to_public_catalog()


def persona_catalog_flat_rows(catalog: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for shelf_key in ("business_area", "development_role"):
        entries = catalog.get(shelf_key)
        if not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            row = dict(e)
            row["shelf"] = shelf_key
            out.append(row)
    return out


