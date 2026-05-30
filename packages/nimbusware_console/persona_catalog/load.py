from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    mapping_to_sorted_table_rows,
    table_rows_csv,
)
import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
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


