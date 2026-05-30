"""Local bundle catalog summaries, tags, and rollups."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH = ".github/workflows/bundle_faiss_index.yml"

_LOCAL_CATALOG_RELPATH = "configs/bundles/catalog.yaml"


def bundle_catalog_local_summary(repo_root: Path) -> dict[str, Any]:
    """One-line operator summary of ``configs/bundles/catalog.yaml`` (no FAISS / no search).

    Returns ``has_catalog_yaml`` (file exists), ``catalog_yaml_relpath``
    (``configs/bundles/catalog.yaml`` when present, else ``None``), ``bundle_count``
    (length of the top-level ``bundles`` list of mappings), and ``distinct_tag_count``
    (case-sensitive distinct strings across each bundle's ``tags`` list). YAML errors
    collapse to zero counts; the path is still reported when the file exists on disk.
    """
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    out: dict[str, Any] = {
        "has_catalog_yaml": path.is_file(),
        "catalog_yaml_relpath": _LOCAL_CATALOG_RELPATH if path.is_file() else None,
        "bundle_count": 0,
        "distinct_tag_count": 0,
    }
    if not out["has_catalog_yaml"]:
        return out
    import yaml

    from hermes_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return out
    if not isinstance(doc, dict):
        return out
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return out
    dict_rows = [b for b in bundles if isinstance(b, dict)]
    out["bundle_count"] = len(dict_rows)
    tags: set[str] = set()
    for b in dict_rows:
        raw_tags = b.get("tags")
        if not isinstance(raw_tags, list):
            continue
        for t in raw_tags:
            if isinstance(t, str) and t.strip():
                tags.add(t.strip())
    out["distinct_tag_count"] = len(tags)
    return out


def bundle_catalog_local_summary_export_filename_slug() -> str:
    """Filename slug prefix for local catalog summary exports."""
    return "bundle_catalog_local_summary"


_BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def _bundle_catalog_local_summary_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def bundle_catalog_local_summary_table_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Sorted field/value rows for local catalog summary export."""
    if not isinstance(summary, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in summary.keys()):
        rows.append(
            {
                "field": key,
                "value": _bundle_catalog_local_summary_cell(summary.get(key)),
            },
        )
    return rows


def bundle_catalog_local_summary_export_json(
    summary: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for local catalog summary."""
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), indent=2, ensure_ascii=False)


def bundle_catalog_local_summary_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize local catalog summary field/value rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS
                },
            )
    return buf.getvalue()


_BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def bundle_catalog_local_summary_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`bundle_catalog_local_summary` output (§14 #12)."""
    metrics: dict[str, Any] = {
        "has_catalog_yaml": False,
        "catalog_yaml_present": False,
        "bundle_count": 0,
        "distinct_tag_count": 0,
        "avg_tags_per_bundle": 0.0,
    }
    if not isinstance(summary, Mapping):
        return metrics
    has_yaml = summary.get("has_catalog_yaml") is True
    metrics["has_catalog_yaml"] = has_yaml
    metrics["catalog_yaml_present"] = has_yaml
    bc = summary.get("bundle_count")
    if isinstance(bc, int) and not isinstance(bc, bool) and bc >= 0:
        metrics["bundle_count"] = bc
    dtc = summary.get("distinct_tag_count")
    if isinstance(dtc, int) and not isinstance(dtc, bool) and dtc >= 0:
        metrics["distinct_tag_count"] = dtc
    if metrics["bundle_count"] > 0:
        metrics["avg_tags_per_bundle"] = round(
            metrics["distinct_tag_count"] / metrics["bundle_count"],
            2,
        )
    return metrics


def bundle_catalog_local_summary_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "Catalog YAML present",
            "value": str(metrics.get("catalog_yaml_present", False)).lower(),
        },
        {"field": "Bundle count", "value": str(metrics.get("bundle_count", 0))},
        {
            "field": "Distinct tag count",
            "value": str(metrics.get("distinct_tag_count", 0)),
        },
    ]
    avg = metrics.get("avg_tags_per_bundle")
    if isinstance(avg, (int, float)) and not isinstance(avg, bool):
        rows.append({"field": "Distinct tags / bundle", "value": str(avg)})
    return rows


def bundle_catalog_local_summary_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of :func:`bundle_catalog_local_summary_operator_metrics`."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def bundle_catalog_local_summary_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize local catalog summary operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def bundle_catalog_local_summary_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when local catalog YAML is present."""
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("catalog_yaml_present") is not True:
        return None
    bc = metrics.get("bundle_count", 0)
    dtc = metrics.get("distinct_tag_count", 0)
    if not isinstance(bc, int) or isinstance(bc, bool):
        bc = 0
    if not isinstance(dtc, int) or isinstance(dtc, bool):
        dtc = 0
    return (
        f"Local catalog operator metrics: **{bc}** bundle(s), "
        f"**{dtc}** distinct tag(s)."
    )


def bundle_catalog_local_summary_operator_metrics_export_filename_slug() -> str:
    """Stable slug for local catalog summary operator metrics downloads."""
    return "bundle_catalog_local_summary_operator_metrics"


def bundle_catalog_distinct_tags_sample(
    repo_root: Path,
    *,
    max_n: int = 12,
) -> list[str]:
    """Sorted, deduped sample of tag strings from ``configs/bundles/catalog.yaml``.

    Reads the same local catalog as :func:`bundle_catalog_local_summary` and pulls
    ``bundles[*].tags`` entries that are non-empty strings. Tags are normalised by
    stripping surrounding whitespace, deduped case-sensitively, sorted alphabetically,
    and truncated to ``max_n`` for caption safety. Returns ``[]`` when the catalog is
    missing, malformed, or unreadable (same swallow pattern as the summary helper).
    """
    if max_n <= 0:
        return []
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
    """Top-``N`` tag-frequency rows from ``configs/bundles/catalog.yaml``.

    Reads the same local catalog as :func:`bundle_catalog_distinct_tags_sample` and counts
    each non-empty string under ``bundles[*].tags`` (whitespace stripped, case-sensitive).
    Returns ``[{"tag": ..., "count": ...}, ...]`` ordered by ``count`` descending, with
    alphabetical tie-break, truncated to ``top_n``. Returns ``[]`` when the catalog is
    missing / malformed / unreadable, when ``bundles`` is not a list, or when ``top_n`` is
    not a positive integer (same swallow pattern as ``bundle_catalog_local_summary`` /
    ``bundle_catalog_distinct_tags_sample``).
    """
    if top_n <= 0:
        return []
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
    """Pretty JSON for top-tag count rows (operator download)."""
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
    """Serialize top-tag count rows to CSV (UTF-8 text)."""
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
    """Sorted, deduped sample of bundle ``id`` strings from ``configs/bundles/catalog.yaml``.

    Reads the same local catalog as :func:`bundle_catalog_distinct_tags_sample` and pulls
    ``bundles[*].id`` entries that are non-empty strings. Ids are normalised by
    stripping surrounding whitespace, deduped case-sensitively, sorted alphabetically,
    and truncated to ``max_n`` for caption safety. Returns ``[]`` when the catalog is
    missing, malformed, or unreadable (same swallow pattern as the sibling helpers).
    """
    if max_n <= 0:
        return []
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
    """One-line caption ``"Distinct tags: N."`` for the local bundle catalog.

    Reads ``bundle_catalog_local_summary(repo_root)["distinct_tag_count"]`` and
    returns the caption only when the value is a non-negative integer **and**
    ``> 0``. Returns ``None`` when the catalog is missing / malformed / unreadable
    (``bundle_catalog_local_summary`` collapses those to zero counts), when the
    summary lacks ``distinct_tag_count``, when the value is not an ``int``
    (``bool`` excluded), or when it is ``0``.

    Complements the existing ``Top tags`` distinct-tags sample caption / dataframe
    with the bare distinct-tag total.
    """
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
    """Composite caption ``"Top tags: <a> (<n>), <b> (<m>), <c> (<k>)."`` for the catalog.

    Reuses :func:`bundle_catalog_top_tag_counts` and renders its rows inline as a
    single operator caption (complements the existing **Top tags** ``st.dataframe``
    that already enumerates the same rows).

    Returns ``None`` whenever ``bundle_catalog_top_tag_counts`` returns ``[]`` —
    i.e. the catalog is missing / malformed / unreadable, ``bundles`` is not a list,
    the root is not a mapping, ``top_n`` is non-positive, or no bundle carries a
    usable string tag.
    """
    rows = bundle_catalog_top_tag_counts(repo_root, top_n=top_n)
    if not rows:
        return None
    parts = [f"{row['tag']} ({row['count']})" for row in rows]
    return "Top tags: " + ", ".join(parts) + "."


def bundle_catalog_bundle_count_caption(repo_root: Path) -> str | None:
    """Composite caption ``"Bundles: N (M tagged, K untagged)."`` for the local catalog.

    ``N`` is the total bundle count (number of mapping entries under ``bundles``), ``K``
    is :func:`bundle_catalog_bundles_without_tags_count`, and ``M = N - K``. Both legs
    use the same inclusion rule (mapping entries only) so the breakdown adds back to
    the total.

    Returns ``None`` (so callers can wire ``if cap is not None``) when:

    * the catalog file is missing,
    * loading raises (``OSError`` / ``ValueError`` / ``UnicodeDecodeError`` /
      ``yaml.YAMLError``),
    * the root is not a mapping,
    * ``bundles`` is not a list, or
    * the bundle count rounds to zero (nothing worth reporting).
    """
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return None
    import yaml

    from hermes_orchestrator.merge import load_yaml

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


def bundle_catalog_bundles_without_tags_count(repo_root: Path) -> int:
    """Count bundle entries in ``configs/bundles/catalog.yaml`` with no usable tags.

    A bundle is counted as "without tags" when its ``tags`` field is **missing**, **not a
    list**, **empty**, or contains **only** non-string / whitespace-only entries (mirrors
    the inclusion rule used by :func:`bundle_catalog_distinct_tags_sample` /
    :func:`bundle_catalog_top_tag_counts`, so each bundle either contributes to the tag
    rollups or to this count, never both).

    Returns ``0`` when the catalog is missing, malformed, unreadable, or when ``bundles``
    is not a list (same swallow pattern as the sibling helpers).
    """
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return 0
    import yaml

    from hermes_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return 0
    if not isinstance(doc, dict):
        return 0
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return 0
    without = 0
    for b in bundles:
        if not isinstance(b, dict):
            continue
        raw_tags = b.get("tags")
        if not isinstance(raw_tags, list):
            without += 1
            continue
        usable = any(
            isinstance(t, str) and t.strip()
            for t in raw_tags
        )
        if not usable:
            without += 1
    return without


def bundle_catalog_bundles_without_tags_caption(repo_root: Path) -> str | None:
    """One-line when catalog bundles lack usable tags.

    See :func:`bundle_catalog_bundles_without_tags_count`.
    """
    without = bundle_catalog_bundles_without_tags_count(repo_root)
    if without <= 0:
        return None
    total = bundle_catalog_local_summary(repo_root).get("bundle_count")
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        return f"Bundles without tags: **{without}**."
    return f"Bundles without tags: **{without}** of **{total}**."


def bundle_catalog_bundles_without_tags_rollup(repo_root: Path) -> dict[str, Any]:
    """Rollup of local catalog summary plus tagged vs untagged bundle counts."""
    summary = bundle_catalog_local_summary(repo_root)
    without = bundle_catalog_bundles_without_tags_count(repo_root)
    total = summary.get("bundle_count")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        total = 0
    return {
        "has_catalog_yaml": summary.get("has_catalog_yaml"),
        "catalog_yaml_relpath": summary.get("catalog_yaml_relpath"),
        "bundle_count": total,
        "distinct_tag_count": summary.get("distinct_tag_count"),
        "bundles_without_tags_count": without,
        "bundles_with_tags_count": max(total - without, 0),
    }


def bundle_catalog_bundles_without_tags_rollup_export_filename_slug() -> str:
    """Filename slug prefix for bundles-without-tags rollup exports."""
    return "bundle_catalog_bundles_without_tags"


def bundle_catalog_bundles_without_tags_rollup_table_rows(
    rollup: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Sorted field/value rows for bundles-without-tags rollup export."""
    if not isinstance(rollup, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in rollup.keys()):
        rows.append(
            {
                "field": key,
                "value": _bundle_catalog_local_summary_cell(rollup.get(key)),
            },
        )
    return rows


def bundle_catalog_bundles_without_tags_rollup_export_json(
    rollup: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for bundles-without-tags rollup."""
    if not isinstance(rollup, Mapping):
        return "{}"
    return json.dumps(dict(rollup), indent=2, ensure_ascii=False)


def bundle_catalog_bundles_without_tags_rollup_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize bundles-without-tags rollup field/value rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def bundle_catalog_bundles_without_tags_rollup_operator_metrics(
    rollup: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`bundle_catalog_bundles_without_tags_rollup` (§14 #12)."""
    metrics: dict[str, Any] = {
        "has_catalog_yaml": False,
        "bundle_count": 0,
        "bundles_without_tags_count": 0,
        "bundles_with_tags_count": 0,
        "untagged_ratio": None,
    }
    if not isinstance(rollup, Mapping):
        return metrics
    metrics["has_catalog_yaml"] = rollup.get("has_catalog_yaml") is True
    bc = rollup.get("bundle_count")
    if isinstance(bc, int) and not isinstance(bc, bool) and bc >= 0:
        metrics["bundle_count"] = bc
    without = rollup.get("bundles_without_tags_count")
    if isinstance(without, int) and not isinstance(without, bool) and without >= 0:
        metrics["bundles_without_tags_count"] = without
    with_tags = rollup.get("bundles_with_tags_count")
    if isinstance(with_tags, int) and not isinstance(with_tags, bool) and with_tags >= 0:
        metrics["bundles_with_tags_count"] = with_tags
    if metrics["bundle_count"] > 0:
        metrics["untagged_ratio"] = round(
            metrics["bundles_without_tags_count"] / metrics["bundle_count"],
            4,
        )
    return metrics


def bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "Catalog YAML present",
            "value": str(metrics.get("has_catalog_yaml", False)).lower(),
        },
        {"field": "Bundle count", "value": str(metrics.get("bundle_count", 0))},
        {
            "field": "Bundles without tags",
            "value": str(metrics.get("bundles_without_tags_count", 0)),
        },
        {
            "field": "Bundles with tags",
            "value": str(metrics.get("bundles_with_tags_count", 0)),
        },
    ]
    ratio = metrics.get("untagged_ratio")
    if isinstance(ratio, (int, float)) and not isinstance(ratio, bool):
        rows.append({"field": "Untagged ratio", "value": str(ratio)})
    return rows


def bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of bundles-without-tags rollup operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def bundle_catalog_bundles_without_tags_rollup_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize bundles-without-tags rollup operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def bundle_catalog_bundles_without_tags_rollup_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when catalog YAML is present with bundle counts."""
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("has_catalog_yaml") is not True:
        return None
    bc = metrics.get("bundle_count", 0)
    without = metrics.get("bundles_without_tags_count", 0)
    if not isinstance(bc, int) or isinstance(bc, bool):
        bc = 0
    if not isinstance(without, int) or isinstance(without, bool):
        without = 0
    return (
        f"Bundles without tags rollup metrics: **{without}** untagged of **{bc}** bundle(s)."
    )


def bundle_catalog_bundles_without_tags_rollup_operator_metrics_export_filename_slug() -> str:
    """Stable slug for bundles-without-tags rollup operator metrics downloads."""
    return "bundle_catalog_bundles_without_tags_rollup_operator_metrics"


def bundle_catalog_bundles_without_id_rollup(repo_root: Path) -> dict[str, Any]:
    """Rollup of local catalog summary plus id vs missing-id bundle counts."""
    summary = bundle_catalog_local_summary(repo_root)
    without = bundle_catalog_bundles_without_id_count(repo_root)
    total = summary.get("bundle_count")
    if not isinstance(total, int) or isinstance(total, bool) or total < 0:
        total = 0
    return {
        "has_catalog_yaml": summary.get("has_catalog_yaml"),
        "catalog_yaml_relpath": summary.get("catalog_yaml_relpath"),
        "bundle_count": total,
        "distinct_tag_count": summary.get("distinct_tag_count"),
        "bundles_without_id_count": without,
        "bundles_with_id_count": max(total - without, 0),
    }


def bundle_catalog_bundles_without_id_rollup_export_filename_slug() -> str:
    """Filename slug prefix for bundles-without-id rollup exports."""
    return "bundle_catalog_bundles_without_id"


def bundle_catalog_bundles_without_id_rollup_table_rows(
    rollup: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Sorted field/value rows for bundles-without-id rollup export."""
    if not isinstance(rollup, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key in sorted(str(k) for k in rollup.keys()):
        rows.append(
            {
                "field": key,
                "value": _bundle_catalog_local_summary_cell(rollup.get(key)),
            },
        )
    return rows


def bundle_catalog_bundles_without_id_rollup_export_json(
    rollup: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON for bundles-without-id rollup."""
    if not isinstance(rollup, Mapping):
        return "{}"
    return json.dumps(dict(rollup), indent=2, ensure_ascii=False)


def bundle_catalog_bundles_without_id_rollup_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize bundles-without-id rollup field/value rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _BUNDLE_CATALOG_LOCAL_SUMMARY_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def bundle_catalog_bundles_without_id_rollup_operator_metrics(
    rollup: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over :func:`bundle_catalog_bundles_without_id_rollup` (§14 #12)."""
    metrics: dict[str, Any] = {
        "has_catalog_yaml": False,
        "bundle_count": 0,
        "bundles_without_id_count": 0,
        "bundles_with_id_count": 0,
    }
    if not isinstance(rollup, Mapping):
        return metrics
    metrics["has_catalog_yaml"] = rollup.get("has_catalog_yaml") is True
    bc = rollup.get("bundle_count")
    if isinstance(bc, int) and not isinstance(bc, bool) and bc >= 0:
        metrics["bundle_count"] = bc
    without = rollup.get("bundles_without_id_count")
    if isinstance(without, int) and not isinstance(without, bool) and without >= 0:
        metrics["bundles_without_id_count"] = without
    with_id = rollup.get("bundles_with_id_count")
    if isinstance(with_id, int) and not isinstance(with_id, bool) and with_id >= 0:
        metrics["bundles_with_id_count"] = with_id
    return metrics


def bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    return [
        {
            "field": "Catalog YAML present",
            "value": str(metrics.get("has_catalog_yaml", False)).lower(),
        },
        {"field": "Bundle count", "value": str(metrics.get("bundle_count", 0))},
        {
            "field": "Bundles without id",
            "value": str(metrics.get("bundles_without_id_count", 0)),
        },
        {
            "field": "Bundles with id",
            "value": str(metrics.get("bundles_with_id_count", 0)),
        },
    ]


def bundle_catalog_bundles_without_id_rollup_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of bundles-without-id rollup operator metrics."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def bundle_catalog_bundles_without_id_rollup_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize bundles-without-id rollup operator metrics rows to CSV."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _BUNDLE_CATALOG_LOCAL_SUMMARY_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def bundle_catalog_bundles_without_id_rollup_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when catalog YAML is present with bundle counts."""
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("has_catalog_yaml") is not True:
        return None
    bc = metrics.get("bundle_count", 0)
    without = metrics.get("bundles_without_id_count", 0)
    if not isinstance(bc, int) or isinstance(bc, bool):
        bc = 0
    if not isinstance(without, int) or isinstance(without, bool):
        without = 0
    return (
        f"Bundles without id rollup metrics: **{without}** without id of **{bc}** bundle(s)."
    )


def bundle_catalog_bundles_without_id_rollup_operator_metrics_export_filename_slug() -> str:
    """Stable slug for bundles-without-id rollup operator metrics downloads."""
    return "bundle_catalog_bundles_without_id_rollup_operator_metrics"


def bundle_catalog_bundles_without_id_caption(repo_root: Path) -> str | None:
    """One-line when catalog bundles lack a usable ``id``.

    See :func:`bundle_catalog_bundles_without_id_count`.
    """
    without = bundle_catalog_bundles_without_id_count(repo_root)
    if without <= 0:
        return None
    total = bundle_catalog_local_summary(repo_root).get("bundle_count")
    if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
        return f"Bundles without id: **{without}**."
    return f"Bundles without id: **{without}** of **{total}**."


def bundle_catalog_bundles_without_id_count(repo_root: Path) -> int:
    """Count bundle entries in ``configs/bundles/catalog.yaml`` with no usable ``id``.

    A bundle is counted when ``id`` is **missing**, **not a string**, or **whitespace-only**
    after stripping (mirrors the inclusion rule used by :func:`bundle_catalog_bundle_ids_sample`,
    so each mapping bundle either contributes to the id sample helper or to this count).

    Returns ``0`` when the catalog is missing, malformed, unreadable, or when ``bundles``
    is not a list (same swallow pattern as :func:`bundle_catalog_bundles_without_tags_count`).
    """
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return 0
    import yaml

    from hermes_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError):
        return 0
    if not isinstance(doc, dict):
        return 0
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return 0
    without = 0
    for b in bundles:
        if not isinstance(b, dict):
            continue
        raw_id = b.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            without += 1
    return without


def _bundle_faiss_mtime_observability(sync: Mapping[str, Any]) -> dict[str, bool]:
    """Whether catalog/index mtimes are observable for operator sync diagnostics."""
    cat_ns = sync.get("catalog_mtime_ns")
    idx_ns = sync.get("index_max_mtime_ns")
    return {
        "catalog_mtime_observable": cat_ns is not None and not isinstance(cat_ns, bool),
        "index_mtime_observable": idx_ns is not None and not isinstance(idx_ns, bool),
    }


def _bundle_faiss_readiness_summary_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _bundle_faiss_index_status_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _mtime_iso_utc_ns(mtime_ns: int) -> str:
    return datetime.fromtimestamp(mtime_ns / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _file_size_mtime(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"bytes": None, "mtime_ns": None, "mtime_iso": None}
    st = path.stat()
    return {
        "bytes": int(st.st_size),
        "mtime_ns": int(st.st_mtime_ns),
        "mtime_iso": _mtime_iso_utc_ns(int(st.st_mtime_ns)),
    }


def _catalog_bundle_row_counts(repo_root: Path) -> tuple[int | None, int | None, str | None]:
    """Return ``(dict_row_count, nonempty_id_count, load_error)`` for ``catalog.yaml``.

    ``nonempty_id_count`` matches :func:`scripts.build_bundle_faiss_index.build_bundle_faiss_index`
    (bundles with a non-empty string ``id`` after strip).
    """
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return None, None, None
    import yaml

    from hermes_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError) as err:
        return None, None, str(err)
    if not isinstance(doc, dict):
        return None, None, "catalog root is not a mapping"
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return None, None, "bundles is not a list"
    dict_rows = [b for b in bundles if isinstance(b, dict)]
    n_nonempty = 0
    for b in dict_rows:
        bid = b.get("id")
        if isinstance(bid, str) and bid.strip():
            n_nonempty += 1
    return len(dict_rows), n_nonempty, None


def _bundle_order_list_length(path: Path) -> tuple[int | None, str | None]:
    """Parse ``bundle_order.json``; expect a JSON list of bundle ids (build script output)."""
    if not path.is_file():
        return None, None
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        return None, str(err)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        return None, str(err)
    if not isinstance(data, list):
        return None, "bundle_order.json root is not a JSON list"
    return len(data), None


def _catalog_nonempty_stripped_id_set(repo_root: Path) -> tuple[set[str] | None, str | None]:
    """Distinct ``id`` strings (stripped) from mapping rows with non-empty string ``id``."""
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return None, None
    import yaml

    from hermes_orchestrator.merge import load_yaml

    try:
        doc = load_yaml(path)
    except (OSError, ValueError, UnicodeDecodeError, yaml.YAMLError) as err:
        return None, str(err)
    if not isinstance(doc, dict):
        return None, "catalog root is not a mapping"
    bundles = doc.get("bundles")
    if not isinstance(bundles, list):
        return None, "bundles is not a list"
    out: set[str] = set()
    for b in bundles:
        if not isinstance(b, dict):
            continue
        bid = b.get("id")
        if isinstance(bid, str) and bid.strip():
            out.add(bid.strip())
    return out, None


def _bundle_order_duplicate_id_signals(ids: list[str]) -> tuple[int, bool, list[str]]:
    """``(distinct_id_count, has_duplicate_list_order, sorted_dup_id_sample)`` for operators."""
    distinct = len(set(ids))
    has_dup = len(ids) != distinct
    if not has_dup:
        return distinct, False, []
    counts = Counter(ids)
    sample = sorted(k for k, v in counts.items() if v > 1)[:8]
    return distinct, True, sample


def _parse_bundle_order_string_ids(path: Path) -> tuple[list[str] | None, str | None]:
    """``bundle_order.json`` as stripped string ids (same shape as the FAISS build script)."""
    if not path.is_file():
        return None, None
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        return None, str(err)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        return None, str(err)
    if not isinstance(data, list):
        return None, "bundle_order.json root is not a JSON list"
    out: list[str] = []
    for x in data:
        if not isinstance(x, str):
            return None, "bundle_order.json entry is not a string"
        t = x.strip()
        if not t:
            return None, "bundle_order.json contains empty id string"
        out.append(t)
    return out, None


def bundle_search_top_hit_preview_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    """Preview the first bundle hit (id and optional score) after a catalog search."""
    if not isinstance(search_payload, Mapping):
        return None
    hits = search_payload.get("hits")
    if not isinstance(hits, list) or not hits:
        return None
    first = hits[0]
    if not isinstance(first, dict):
        return None
    bid = first.get("id")
    if bid is None or not str(bid).strip():
        return None
    parts = [f"top hit id={str(bid).strip()!r}"]
    score = first.get("score")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        parts.append(f"score={score}")
    return "Bundle search: " + ", ".join(parts) + "."


def bundle_search_k_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    """Bounded ``k`` from a bundle search response when observable."""
    if not isinstance(search_payload, Mapping):
        return None
    q = str(search_payload.get("query", "")).strip()
    if not q:
        return None
    k = search_payload.get("k")
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        return None
    return f"Bundle search k: **{k}**."


def bundle_search_query_length_caption(
    query: str,
    *,
    hit_count: int | None = None,
) -> str | None:
    """Character length of the trimmed bundle search query (optional hit suffix)."""
    if not isinstance(query, str):
        return None
    text = query.strip()
    if not text:
        return None
    n = len(text)
    cap = f"Bundle search query: **{n}** character(s)."
    if isinstance(hit_count, int) and not isinstance(hit_count, bool) and hit_count >= 0:
        word = "hit" if hit_count == 1 else "hits"
        cap = cap[:-1] + f" (**{hit_count}** {word})."
    return cap


def bundle_search_faiss_ready_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    """Dedicated ``faiss_index_ready`` flag from the last bundle search response."""
    if not isinstance(search_payload, Mapping):
        return None
    ready = search_payload.get("faiss_index_ready")
    if ready is True:
        return "Bundle search: FAISS index **ready** on the last response."
    if ready is False:
        return "Bundle search: FAISS index **not ready** on the last response."
    return None


def bundle_search_hits_summary_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    """One-line summary after a catalog search (query, k, hit count, FAISS flags)."""
    if not isinstance(search_payload, Mapping):
        return None
    q = str(search_payload.get("query", "")).strip()
    if not q:
        return None
    k = search_payload.get("k")
    hits = search_payload.get("hits")
    n_hits = len(hits) if isinstance(hits, list) else 0
    parts: list[str] = [f"q={q!r}"]
    if isinstance(k, int) and not isinstance(k, bool):
        parts.append(f"k={k}")
    parts.append(f"hits={n_hits}")
    ready = search_payload.get("faiss_index_ready")
    if ready is True:
        parts.append("faiss_index_ready=yes")
    elif ready is False:
        parts.append("faiss_index_ready=no")
    stale = search_payload.get("faiss_index_stale")
    if stale is True:
        parts.append("faiss_index_stale=yes")
    elif stale is False:
        parts.append("faiss_index_stale=no")
    return "Bundle search: " + " · ".join(parts) + "."


def bundle_search_hit_count_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    """Explicit hit count when ``hits`` is a non-empty list."""
    if not isinstance(search_payload, Mapping):
        return None
    hits = search_payload.get("hits")
    if not isinstance(hits, list) or not hits:
        return None
    n = len(hits)
    word = "hit" if n == 1 else "hits"
    return f"Bundle search: **{n}** {word}."


def bundle_search_after_hits_stale_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    """When a search returned hits but the FAISS index is stale, nudge operators to rebuild.

    Mirrors **GET /v1/bundles/search** ``faiss_index_stale`` semantics (catalog newer than
    index files). Returns ``None`` when there is nothing to warn about.
    """
    if not isinstance(search_payload, Mapping):
        return None
    if search_payload.get("faiss_index_stale") is not True:
        return None
    hits = search_payload.get("hits")
    if not isinstance(hits, list) or not hits:
        return None
    return (
        "FAISS index is **stale** (``catalog.yaml`` newer than ``faiss.index`` / "
        "``bundle_order.json``). Vector ordering in these hits may lag the latest catalog — "
        "rebuild from repo root (see **FAISS index readiness** above; workflow "
        f"``{BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH}``)."
    )


def bundle_search_empty_hits_readiness_caption(
    search_payload: Mapping[str, Any] | None,
) -> str | None:
    """When a non-empty query returned no hits, tie the empty set to FAISS readiness (§14 #12).

    Uses the same ``faiss_index_ready`` flag as :func:`run_bundle_catalog_search` /
    **GET /v1/bundles/search** (index files present vs catalog). Returns ``None`` when there is
    nothing to surface (no query, hits present, or malformed payload).
    """
    if not isinstance(search_payload, Mapping):
        return None
    q = str(search_payload.get("query", "")).strip()
    if not q:
        return None
    hits = search_payload.get("hits")
    if not isinstance(hits, list) or len(hits) != 0:
        return None
    if search_payload.get("faiss_index_ready") is True:
        return (
            "Zero hits for this query with **FAISS index ready** — try a broader ``q`` or "
            "inspect tag coverage in ``configs/bundles/catalog.yaml``."
        )
    return (
        "Zero hits while **FAISS index is not ready** (``faiss.index`` + ``bundle_order.json`` "
        "missing or incomplete vs ``configs/bundles/catalog.yaml``). See **FAISS index readiness** "
        "above; workflow "
        f"``{BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH}``."
    )


def bundle_search_operator_metrics(
    search_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Structured rollup over the last bundle search payload (§14 #12)."""
    metrics: dict[str, Any] = {
        "hit_count": 0,
        "distinct_tag_count": 0,
        "hits_without_tags": 0,
        "hits_without_id": 0,
        "top_hit_id": None,
    }
    if not isinstance(search_payload, Mapping):
        return metrics
    hits = search_payload.get("hits")
    if not isinstance(hits, list):
        return metrics
    tags_seen: set[str] = set()
    hit_count = 0
    for row in hits:
        if not isinstance(row, dict):
            continue
        hit_count += 1
        bid = row.get("id")
        if not isinstance(bid, str) or not bid.strip():
            metrics["hits_without_id"] += 1
        elif metrics["top_hit_id"] is None:
            metrics["top_hit_id"] = bid.strip()
        raw_tags = row.get("tags")
        if not isinstance(raw_tags, list):
            metrics["hits_without_tags"] += 1
            continue
        usable = [t.strip() for t in raw_tags if isinstance(t, str) and t.strip()]
        if not usable:
            metrics["hits_without_tags"] += 1
        else:
            tags_seen.update(usable)
    metrics["hit_count"] = hit_count
    metrics["distinct_tag_count"] = len(tags_seen)
    return metrics


def bundle_search_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Two-column rows for ``st.dataframe`` (field / value)."""
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Hit count", "value": str(metrics.get("hit_count", 0))},
        {"field": "Distinct tags (union)", "value": str(metrics.get("distinct_tag_count", 0))},
        {"field": "Hits without tags", "value": str(metrics.get("hits_without_tags", 0))},
        {"field": "Hits without id", "value": str(metrics.get("hits_without_id", 0))},
    ]
    top = metrics.get("top_hit_id")
    if isinstance(top, str) and top.strip():
        rows.append({"field": "Top hit id", "value": top.strip()})
    return rows


_BUNDLE_SEARCH_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def bundle_search_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    """Pretty JSON export of :func:`bundle_search_operator_metrics` output."""
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def bundle_search_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize operator metrics table rows to CSV (UTF-8 text)."""
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_SEARCH_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _BUNDLE_SEARCH_OPERATOR_METRICS_CSV_COLUMNS},
            )
    return buf.getvalue()


def bundle_search_operator_metrics_export_filename_slug() -> str:
    """Stable slug for bundle search operator metrics downloads."""
    return "bundle_search_operator_metrics"


def bundle_search_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    """One-line operator caption when the last search returned hits."""
    if not isinstance(metrics, Mapping):
        return None
    hc = metrics.get("hit_count")
    if isinstance(hc, bool) or not isinstance(hc, int) or hc < 1:
        return None
    parts = [f"**{hc}** hit(s)", f"**{metrics.get('distinct_tag_count', 0)}** distinct tag(s)"]
    wtags = metrics.get("hits_without_tags", 0)
    wid = metrics.get("hits_without_id", 0)
    if isinstance(wtags, int) and not isinstance(wtags, bool) and wtags > 0:
        parts.append(f"**{wtags}** without tags")
    if isinstance(wid, int) and not isinstance(wid, bool) and wid > 0:
        parts.append(f"**{wid}** without id")
    return "Bundle search operator metrics: " + ", ".join(parts) + "."


def bundle_search_filename_slug(query: str, *, max_len: int = 40) -> str:
    """ASCII-ish slug for download filenames (query portion only)."""
    raw = query.strip().lower().replace(" ", "_")[:max_len]
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "query"
    return slug[:max_len]


_BUNDLE_LOCAL_CSV_COLUMNS: tuple[str, ...] = ("id", "title", "tags")


def bundle_catalog_local_bundles(repo_root: Path) -> list[dict[str, Any]]:
    """Return mapping rows from ``configs/bundles/catalog.yaml`` (no FAISS / no search)."""
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
    """Normalize local catalog bundles to ``id`` / ``title`` / ``tags`` display rows."""
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
    """Pretty JSON for local catalog bundle inventory (normalized rows)."""
    rows = bundle_catalog_local_bundles_table_rows(bundles)
    return json.dumps(rows, indent=2, ensure_ascii=False)


def bundle_catalog_local_bundles_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    """Serialize local catalog bundle rows to CSV (UTF-8 text)."""
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
    """ASCII-ish slug for local catalog export filenames."""
    return bundle_faiss_operator_drilldown_export_filename_slug(repo_root, max_len=max_len)


def bundle_search_hits_from_blob(blob: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Return ``hits`` from a bundle search session blob."""
    if not isinstance(blob, Mapping):
        return []
    raw = blob.get("hits")
    if not isinstance(raw, list):
        return []
    return [h for h in raw if isinstance(h, dict)]


def bundle_search_hits_export_json(hits: Sequence[Mapping[str, Any]]) -> str:
    """Pretty JSON for the hits array only (operator download)."""
    rows = [dict(h) for h in hits if isinstance(h, Mapping)]
    return json.dumps(rows, indent=2, ensure_ascii=False)


def _bundle_search_hit_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts = [str(x).strip() for x in value if isinstance(x, str) and str(x).strip()]
        return ", ".join(parts)
    if isinstance(value, (dict, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


_BUNDLE_SEARCH_HITS_CSV_COLUMNS: tuple[str, ...] = ("id", "title", "tags", "score")


def bundle_search_hits_table_rows_csv(hits: Sequence[Mapping[str, Any]]) -> str:
    """Serialize bundle search hit dicts to CSV (UTF-8 text)."""
    if not hits:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_BUNDLE_SEARCH_HITS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for h in hits:
        if not isinstance(h, Mapping):
            continue
        w.writerow(
            {
                "id": _bundle_search_hit_cell(h.get("id")),
                "title": _bundle_search_hit_cell(h.get("title")),
                "tags": _bundle_search_hit_cell(h.get("tags")),
                "score": _bundle_search_hit_cell(h.get("score")),
            },
        )
    return buf.getvalue()


def run_bundle_catalog_search(repo_root: Path, query: str, *, k: int) -> dict[str, Any]:
    """Run :func:`search_bundles` with bounded ``k``; echo query and ``k`` in the payload."""
    from hermes_extensions.catalog import bundle_faiss_index_sync_state, search_bundles

    kk = max(1, min(20, int(k)))
    q = query.strip()
    sync = bundle_faiss_index_sync_state(repo_root)
    base: dict[str, Any] = {
        "query": q,
        "k": kk,
        "hits": [],
        "faiss_index_ready": bool(sync.get("ready")),
        "faiss_index_stale": sync.get("stale"),
    }
    if not q:
        return base
    hits = search_bundles(repo_root, q, k=kk)
    base["hits"] = hits
    return base
