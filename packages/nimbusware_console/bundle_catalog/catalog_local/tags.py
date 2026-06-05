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
from nimbusware_console.bundle_catalog.catalog_local.rollup_without_tags import (
    bundle_catalog_bundles_without_tags_count,
)
from nimbusware_console.bundle_catalog.catalog_local.summary import (
    bundle_catalog_local_summary,
)


def bundle_catalog_distinct_tags_sample(
    repo_root: Path,
    *,
    max_n: int = 12,
) -> list[str]:
    if max_n <= 0:
        return []
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return []
    import yaml

    from nimbusware_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return []
    if not isinstance(doc, dict):
        return []
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return []
    tags: set[str] = set()
    for b in bundles:
        if not isinstance(b, dict):
            continue
        raw_tags = b.get("tags")
        if not isinstance(raw_tags, list):
            continue
        for t in raw_tags:
            if isinstance(t, str):
                trimmed = t.strip()
                if trimmed:
                    tags.add(trimmed)
    return sorted(tags)[:max_n]


_BUNDLE_TOP_TAG_COUNTS_CSV_COLUMNS: tuple[str, ...] = ("tag", "count")


def bundle_catalog_top_tag_counts(
    repo_root: Path,
    *,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    if top_n <= 0:
        return []
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return []
    import yaml

    from nimbusware_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return []
    if not isinstance(doc, dict):
        return []
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return []
    counts: dict[str, int] = {}
    for b in bundles:
        if not isinstance(b, dict):
            continue
        raw_tags = b.get("tags")
        if not isinstance(raw_tags, list):
            continue
        for t in raw_tags:
            if not isinstance(t, str):
                continue
            trimmed = t.strip()
            if not trimmed:
                continue
            counts[trimmed] = counts.get(trimmed, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"tag": tag, "count": count} for tag, count in ordered[:top_n]]


def bundle_catalog_top_tag_counts_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def bundle_catalog_top_tag_counts_table_rows_csv(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_TOP_TAG_COUNTS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if not isinstance(r, Mapping):
            continue
        w.writerow(
            {
                "tag": _bundle_search_hit_cell(r.get("tag")),
                "count": _bundle_search_hit_cell(r.get("count")),
            },
        )
    return buf.getvalue()


def bundle_catalog_bundle_ids_sample(
    repo_root: Path,
    *,
    max_n: int = 12,
) -> list[str]:
    if max_n <= 0:
        return []
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return []
    import yaml

    from nimbusware_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return []
    if not isinstance(doc, dict):
        return []
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return []
    ids: set[str] = set()
    for b in bundles:
        if not isinstance(b, dict):
            continue
        raw_id = b.get("id")
        if isinstance(raw_id, str):
            trimmed = raw_id.strip()
            if trimmed:
                ids.add(trimmed)
    return sorted(ids)[:max_n]


def bundle_catalog_distinct_tag_count_caption(repo_root: Path) -> str | None:
    summary = bundle_catalog_local_summary(repo_root)
    if not isinstance(summary, Mapping):
        return None
    raw = summary.get("distinct_tag_count")
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    if raw <= 0:
        return None
    return f"Distinct tags: {raw}."


def bundle_catalog_top_tag_caption(
    repo_root: Path,
    *,
    top_n: int = 3,
) -> str | None:
    rows = bundle_catalog_top_tag_counts(repo_root, top_n=top_n)
    if not rows:
        return None
    parts = [f"{row['tag']} ({row['count']})" for row in rows]
    return "Top tags: " + ", ".join(parts) + "."


def bundle_catalog_bundle_count_caption(repo_root: Path) -> str | None:
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return None
    import yaml

    from nimbusware_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return None
    if not isinstance(doc, dict):
        return None
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return None
    total = sum(1 for b in bundles if isinstance(b, dict))
    if total <= 0:
        return None
    untagged = bundle_catalog_bundles_without_tags_count(repo_root)
    tagged = max(total - untagged, 0)
    return f"Bundles: {total} ({tagged} tagged, {untagged} untagged)."
