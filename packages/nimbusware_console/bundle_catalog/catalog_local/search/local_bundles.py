from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import partial
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _bundle_search_hit_cell,
)
from nimbusware_console.bundle_catalog.catalog_local._load import (
    catalog_bundle_rows,
    load_catalog_doc,
)
from nimbusware_console.bundle_catalog.catalog_local.search.metrics import (
    _BUNDLE_LOCAL_CSV_COLUMNS,
)
from nimbusware_console.components.operator_metrics import table_rows_csv


def bundle_catalog_local_bundles(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> list[dict[str, Any]]:
    return catalog_bundle_rows(
        load_catalog_doc(repo_root, config_materializer=config_materializer),
    )


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


bundle_catalog_local_bundles_table_rows_csv = partial(
    table_rows_csv,
    columns=_BUNDLE_LOCAL_CSV_COLUMNS,
)


def bundle_catalog_local_export_filename_slug(
    repo_root: Path,
    *,
    max_len: int = 40,
) -> str:
    from nimbusware_console.bundle_catalog.faiss_status import (
        bundle_faiss_operator_drilldown_export_filename_slug,
    )

    return bundle_faiss_operator_drilldown_export_filename_slug(repo_root, max_len=max_len)
