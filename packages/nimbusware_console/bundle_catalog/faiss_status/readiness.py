from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _bundle_faiss_readiness_summary_cell,
)
from nimbusware_console.bundle_catalog.catalog_local.faiss_helpers import (
    _bundle_faiss_mtime_observability,
)
from nimbusware_console.bundle_catalog.faiss_status.drilldown.core import (
    bundle_faiss_operator_drilldown_export_filename_slug,
)
from nimbusware_console.bundle_catalog.faiss_status.index_status import (
    bundle_faiss_index_status,
)
from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_to_sorted_table_rows,
    table_rows_csv,
)
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports


def bundle_faiss_readiness_summary(repo_root: Path) -> dict[str, Any]:
    sync = bundle_faiss_index_status(repo_root)
    mtime_flags = _bundle_faiss_mtime_observability(sync)
    cat_ok = bool(sync.get("catalog_exists"))
    faiss_ex = bool(sync.get("faiss_index_exists"))
    meta_ex = bool(sync.get("bundle_order_exists"))
    stale = sync.get("stale")
    ready_files = faiss_ex and meta_ex

    if not cat_ok:
        return {
            "code": "no_catalog",
            "headline": "Bundle catalog file missing",
            "detail": (
                "Expected ``configs/bundles/catalog.yaml`` under the repo root. "
                "Cannot build or search until it exists."
            ),
            "missing": ["configs/bundles/catalog.yaml"],
            **mtime_flags,
        }

    missing: list[str] = []
    if not faiss_ex:
        missing.append("configs/bundles/index/faiss.index")
    if not meta_ex:
        missing.append("configs/bundles/index/bundle_order.json")

    if not ready_files:
        return {
            "code": "incomplete",
            "headline": "FAISS index files incomplete",
            "detail": (
                "Vector search stays off until both ``faiss.index`` and ``bundle_order.json`` "
                "exist (run the build script or ``scripts/faiss/build_bundle_faiss_index.ps1``)."
            ),
            "missing": missing,
            **mtime_flags,
        }

    if stale is True:
        return {
            "code": "stale",
            "headline": "FAISS index may be out of date",
            "detail": (
                "``catalog.yaml`` is newer than the index files on disk. Rebuild after "
                "catalog edits so vector hits match tags."
            ),
            "missing": [],
            "auto_rebuild_recommended": True,
            **mtime_flags,
        }

    return {
        "code": "ready",
        "headline": "FAISS index present and fresh enough",
        "detail": (
            "Both index files exist and catalog is not newer than the index. "
            "Vector top-k still requires ``faiss`` installed at runtime."
        ),
        "missing": [],
        **mtime_flags,
    }


def bundle_faiss_readiness_summary_export_json(repo_root: Path) -> str:
    summ = bundle_faiss_readiness_summary(repo_root)
    if not isinstance(summ, Mapping):
        return "{}"
    return json.dumps(dict(summ), ensure_ascii=False, indent=2)


def bundle_faiss_readiness_summary_table_rows(
    summary: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return mapping_to_sorted_table_rows(summary, _bundle_faiss_readiness_summary_cell)


def bundle_faiss_readiness_summary_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def bundle_faiss_readiness_summary_operator_metrics(
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "code": None,
        "missing_path_count": 0,
        "is_ready": False,
        "is_stale": False,
        "is_incomplete": False,
        "is_no_catalog": False,
        "catalog_mtime_observable": False,
        "index_mtime_observable": False,
        "mtime_both_observable": False,
        "headline_present": False,
        "auto_rebuild_recommended": False,
    }
    if not isinstance(summary, Mapping):
        return metrics
    code = summary.get("code")
    if isinstance(code, str) and code.strip():
        code_s = code.strip()
        metrics["code"] = code_s
        metrics["is_ready"] = code_s == "ready"
        metrics["is_stale"] = code_s == "stale"
        metrics["is_incomplete"] = code_s == "incomplete"
        metrics["is_no_catalog"] = code_s == "no_catalog"
    missing = summary.get("missing")
    if isinstance(missing, list):
        metrics["missing_path_count"] = len(missing)
    if summary.get("catalog_mtime_observable") is True:
        metrics["catalog_mtime_observable"] = True
    if summary.get("index_mtime_observable") is True:
        metrics["index_mtime_observable"] = True
    if metrics["catalog_mtime_observable"] and metrics["index_mtime_observable"]:
        metrics["mtime_both_observable"] = True
    headline = summary.get("headline")
    if isinstance(headline, str) and headline.strip():
        metrics["headline_present"] = True
    if summary.get("auto_rebuild_recommended") is True:
        metrics["auto_rebuild_recommended"] = True
    return metrics


def bundle_faiss_readiness_summary_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    code = metrics.get("code")
    if isinstance(code, str) and code.strip():
        rows.append({"field": "Readiness code", "value": code.strip()})
    rows.append(
        {"field": "Missing paths", "value": str(metrics.get("missing_path_count", 0))},
    )
    for label, key in (
        ("Ready", "is_ready"),
        ("Stale", "is_stale"),
        ("Incomplete", "is_incomplete"),
        ("No catalog", "is_no_catalog"),
    ):
        if metrics.get(key) is True:
            rows.append({"field": label, "value": "yes"})
    for label, key in (
        ("Catalog mtime observable", "catalog_mtime_observable"),
        ("Index mtime observable", "index_mtime_observable"),
        ("Both mtimes observable", "mtime_both_observable"),
        ("Headline present", "headline_present"),
    ):
        if metrics.get(key) is True:
            rows.append({"field": label, "value": "yes"})
    return rows


(
    bundle_faiss_readiness_summary_operator_metrics_export_json,
    bundle_faiss_readiness_summary_operator_metrics_table_rows_csv,
    bundle_faiss_readiness_summary_operator_metrics_export_filename_slug,
) = bind_operator_metrics_exports(
    export_slug="bundle_faiss_readiness_summary_operator_metrics",
)


def bundle_faiss_readiness_summary_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    code = metrics.get("code")
    if not isinstance(code, str) or not code.strip():
        return None
    missing = metrics.get("missing_path_count", 0)
    if not isinstance(missing, int) or isinstance(missing, bool):
        missing = 0
    parts = [f"FAISS readiness metrics: **{code.strip()}**"]
    if missing > 0:
        parts.append(f"**{missing}** missing path(s)")
    if metrics.get("is_stale") is True:
        parts.append("index **stale** (catalog newer than index)")
    if metrics.get("is_incomplete") is True:
        parts.append("index **incomplete**")
    if metrics.get("is_no_catalog") is True:
        parts.append("**no catalog** (FAISS index cannot be built)")
    if metrics.get("catalog_mtime_observable") is True:
        parts.append("catalog mtime observable")
    if metrics.get("index_mtime_observable") is True:
        parts.append("index mtime observable")
    if metrics.get("mtime_both_observable") is True:
        parts.append("catalog+index mtime **both observable**")
    if metrics.get("headline_present") is True:
        parts.append("headline present")
    return ", ".join(parts) + "."


def bundle_faiss_readiness_export_filename_slug(
    repo_root: Path,
    *,
    max_len: int = 36,
) -> str:
    return bundle_faiss_operator_drilldown_export_filename_slug(repo_root, max_len=max_len)


def bundle_faiss_readiness_code_caption(repo_root: Path) -> str | None:
    summ = bundle_faiss_readiness_summary(repo_root)
    code = summ.get("code")
    if not isinstance(code, str) or not code.strip():
        return None
    return f"FAISS readiness bucket: {code.strip()}."


def bundle_faiss_readiness_headline_caption(repo_root: Path) -> str | None:
    summ = bundle_faiss_readiness_summary(repo_root)
    headline = summ.get("headline")
    if not isinstance(headline, str):
        return None
    text = headline.strip()
    if not text:
        return None
    return f"FAISS readiness: {text}."


def bundle_faiss_readiness_missing_caption(
    repo_root: Path,
    *,
    max_paths: int = 3,
) -> str | None:
    summ = bundle_faiss_readiness_summary(repo_root)
    missing = summ.get("missing")
    if not isinstance(missing, list) or not missing:
        return None
    paths = [str(p).strip() for p in missing if isinstance(p, str) and str(p).strip()]
    if not paths:
        return None
    limit = max_paths if max_paths > 0 else 3
    shown = paths[:limit]
    body = ", ".join(f"``{p}``" for p in shown)
    extra = len(paths) - len(shown)
    if extra > 0:
        suffix = "path" if extra == 1 else "paths"
        body = f"{body} (+{extra} more {suffix})"
    return f"FAISS index missing: {body}."


_FAISS_READINESS_MISSING_PATHS_CSV_COLUMNS: tuple[str, ...] = ("path",)


def bundle_faiss_readiness_missing_paths_table_rows(
    summary: Mapping[str, Any],
) -> list[dict[str, str]]:
    if not isinstance(summary, Mapping):
        return []
    missing = summary.get("missing")
    if not isinstance(missing, list) or not missing:
        return []
    out: list[dict[str, str]] = []
    for p in missing:
        if isinstance(p, str) and p.strip():
            out.append({"path": p.strip()})
    return out


def bundle_faiss_readiness_missing_paths_export_json(
    rows: Sequence[Mapping[str, Any]],
) -> str:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return "[]"
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(dict(r))
    return json.dumps(out, indent=2, ensure_ascii=False)


def bundle_faiss_readiness_missing_paths_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return table_rows_csv(rows, _FAISS_READINESS_MISSING_PATHS_CSV_COLUMNS)
