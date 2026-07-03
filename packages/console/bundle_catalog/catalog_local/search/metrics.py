from __future__ import annotations

import re

from console.explainer_core.generic_display_metrics import (
    bundle_search_operator_metrics,  # noqa: F401
    bundle_search_operator_metrics_caption,  # noqa: F401
    bundle_search_operator_metrics_export_filename_slug,  # noqa: F401
    bundle_search_operator_metrics_export_json,  # noqa: F401
    bundle_search_operator_metrics_table_rows,  # noqa: F401
    bundle_search_operator_metrics_table_rows_csv,  # noqa: F401
)


def bundle_search_filename_slug(query: str, *, max_len: int = 40) -> str:
    raw = query.strip().lower().replace(" ", "_")[:max_len]
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "query"
    return slug[:max_len]


_BUNDLE_LOCAL_CSV_COLUMNS: tuple[str, ...] = ("id", "title", "tags")
