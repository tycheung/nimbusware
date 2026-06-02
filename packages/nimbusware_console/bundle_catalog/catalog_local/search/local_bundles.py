from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _bundle_search_hit_cell,
)
from nimbusware_console.bundle_catalog.catalog_local.search.metrics import (
    _BUNDLE_LOCAL_CSV_COLUMNS,
)


def bundle_catalog_local_bundles(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return []
    import yaml

    from hermes_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return []
    if not isinstance(doc, dict):
        return []
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return []
    return [b for b in bundles if isinstance(b, dict)]


def bundle_catalog_local_bundles_table_rows(
    bundles: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for b in bundles:
        if not isinstance(b, Mapping):
            continue
        rows.append(
            {
                "id": _bundle_search_hit_cell(b.get("id")),
                "title": _bundle_search_hit_cell(b.get("title")),
                "tags": _bundle_search_hit_cell(b.get("tags")),
            },
        )
    return rows


def bundle_catalog_local_bundles_export_json(
    bundles: Sequence[Mapping[str, Any]],
) -> str:
    rows = bundle_catalog_local_bundles_table_rows(bundles)
    return json.dumps(rows, indent=2, ensure_ascii=False)


def bundle_catalog_local_bundles_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_LOCAL_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _BUNDLE_LOCAL_CSV_COLUMNS})
    return buf.getvalue()


def bundle_catalog_local_export_filename_slug(
    repo_root: Path,
    *,
    max_len: int = 40,
) -> str:
    from nimbusware_console.bundle_catalog.faiss_status import (
        bundle_faiss_operator_drilldown_export_filename_slug,
    )

    return bundle_faiss_operator_drilldown_export_filename_slug(repo_root, max_len=max_len)
