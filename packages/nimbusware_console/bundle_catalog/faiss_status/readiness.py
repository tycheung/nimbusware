from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import partial
from pathlib import Path
from typing import Any

from agent_core.coercion import as_stripped_str, is_strict_int
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
from nimbusware_console.explainer_core.operator_metrics_exports import (
    build_metrics_fn,
    install_operator_metrics_module,
)


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


bundle_faiss_readiness_summary_table_rows_csv = field_value_table_rows_csv


_FAISS_READINESS_PREFIX = "bundle_faiss_readiness_summary"

_FAISS_READINESS_DEFAULTS: dict[str, Any] = {
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


def _faiss_readiness_postprocess(
    metrics: dict[str, Any],
    summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    code = metrics.get("code")
    if isinstance(code, str) and code.strip():
        code_s = code.strip()
        metrics["is_ready"] = code_s == "ready"
        metrics["is_stale"] = code_s == "stale"
        metrics["is_incomplete"] = code_s == "incomplete"
        metrics["is_no_catalog"] = code_s == "no_catalog"
    if metrics["catalog_mtime_observable"] and metrics["index_mtime_observable"]:
        metrics["mtime_both_observable"] = True
    return metrics


def _faiss_readiness_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    code = as_stripped_str(metrics.get("code"))
    if code is not None:
        rows.append({"field": "Readiness code", "value": code})
    rows.append(
        {"field": "Missing paths", "value": str(metrics.get("missing_path_count", 0))},
    )
    for label, key in (
        ("Ready", "is_ready"),
        ("Stale", "is_stale"),
        ("Incomplete", "is_incomplete"),
        ("No catalog", "is_no_catalog"),
        ("Catalog mtime observable", "catalog_mtime_observable"),
        ("Index mtime observable", "index_mtime_observable"),
        ("Both mtimes observable", "mtime_both_observable"),
        ("Headline present", "headline_present"),
    ):
        if metrics.get(key) is True:
            rows.append({"field": label, "value": "yes"})
    return rows


def _faiss_readiness_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    code = as_stripped_str(metrics.get("code"))
    if code is None:
        return None
    missing = metrics.get("missing_path_count", 0)
    if not is_strict_int(missing):
        missing = 0
    parts = [f"FAISS readiness metrics: **{code}**"]
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


(
    bundle_faiss_readiness_summary_operator_metrics,
    bundle_faiss_readiness_summary_operator_metrics_table_rows,
    bundle_faiss_readiness_summary_operator_metrics_caption,
    bundle_faiss_readiness_summary_operator_metrics_export_json,
    bundle_faiss_readiness_summary_operator_metrics_table_rows_csv,
    _bundle_faiss_readiness_summary_operator_metrics_export_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix=_FAISS_READINESS_PREFIX,
    metrics=build_metrics_fn(
        _FAISS_READINESS_DEFAULTS,
        str_strip_fields=(("code", "code"),),
        list_len_fields=(("missing", "missing_path_count"),),
        bool_fields=(
            ("catalog_mtime_observable", "catalog_mtime_observable"),
            ("index_mtime_observable", "index_mtime_observable"),
            ("auto_rebuild_recommended", "auto_rebuild_recommended"),
        ),
        str_present=(("headline", "headline_present"),),
        postprocess=_faiss_readiness_postprocess,
    ),
    table_rows=_faiss_readiness_operator_metrics_table_rows,
    caption=_faiss_readiness_operator_metrics_caption,
)


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


bundle_faiss_readiness_missing_paths_table_rows_csv = partial(
    table_rows_csv, columns=_FAISS_READINESS_MISSING_PATHS_CSV_COLUMNS
)
