from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.faiss_status._constants import (
    BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH,
)
from nimbusware_console.explainer_core.operator_metrics_exports import (
    build_metrics_fn,
    install_operator_metrics_module,
)

_PREFIX = "bundle_faiss_index_status"

_DEFAULTS: dict[str, Any] = {
    "ready": False,
    "stale": None,
    "faiss_index_exists": False,
    "bundle_order_exists": False,
}

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("FAISS ready", "ready"),
    ("Index stale vs catalog", "stale"),
    ("faiss.index on disk", "faiss_index_exists"),
    ("bundle_order.json on disk", "bundle_order_exists"),
)


def _faiss_index_status_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    if metrics.get("ready") is True:
        rows.append({"field": "FAISS ready", "value": "yes"})
    stale = metrics.get("stale")
    if isinstance(stale, bool):
        rows.append({"field": "Index stale vs catalog", "value": str(stale).lower()})
    if metrics.get("faiss_index_exists") is True:
        rows.append({"field": "faiss.index on disk", "value": "yes"})
    if metrics.get("bundle_order_exists") is True:
        rows.append({"field": "bundle_order.json on disk", "value": "yes"})
    return rows


def _faiss_index_status_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("ready") is not True:
        return "FAISS index: **not ready** (rebuild recommended)."
    stale = metrics.get("stale")
    if stale is True:
        return "FAISS index: **ready** but **stale** vs catalog."
    if stale is False:
        return "FAISS index: **ready** and in sync with catalog."
    return "FAISS index: **ready**."


(
    bundle_faiss_index_status_operator_metrics,
    bundle_faiss_index_status_operator_metrics_table_rows,
    bundle_faiss_index_status_operator_metrics_caption,
    bundle_faiss_index_status_operator_metrics_export_json,
    bundle_faiss_index_status_operator_metrics_table_rows_csv,
    _bundle_faiss_index_status_operator_metrics_export_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix=_PREFIX,
    metrics=build_metrics_fn(
        _DEFAULTS,
        bool_fields=(
            ("ready", "ready"),
            ("faiss_index_exists", "faiss_index_exists"),
            ("bundle_order_exists", "bundle_order_exists"),
        ),
        bool_value_fields=(("stale", "stale"),),
    ),
    table_rows=_faiss_index_status_operator_metrics_table_rows,
    caption=_faiss_index_status_operator_metrics_caption,
)


def bundle_faiss_index_workflow_caption_note() -> str:
    return (
        f"Weekly / manual smoke: repo file ``{BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH}`` "
        "(workflow name **bundle_faiss_index**)."
    )


def bundle_faiss_build_command_snippet() -> str:
    return (
        "poetry install --with faiss\n"
        "poetry run python scripts/faiss/build_bundle_faiss_index.py\n"
        "# poetry run python scripts/faiss/build_bundle_faiss_index.py --help"
    )


def bundle_faiss_build_command_snippet_explicit(repo_root: Path) -> str:
    root_s = str(repo_root.resolve())
    return (
        "poetry install --with faiss\n"
        f'poetry run python scripts/faiss/build_bundle_faiss_index.py --repo-root "{root_s}"\n'
        "# poetry run python scripts/faiss/build_bundle_faiss_index.py --help"
    )


def bundle_faiss_build_powershell_snippet_explicit(repo_root: Path) -> str:
    root_s = str(repo_root.resolve())
    return (
        "poetry install --with faiss\n"
        f'poetry run python scripts/faiss/build_bundle_faiss_index.py --repo-root "{root_s}"\n'
        f'# Or: .\\scripts\\build_bundle_faiss_index.ps1 -RepoRoot "{root_s}"'
    )


def bundle_faiss_invoke_ps1_snippet_explicit(repo_root: Path) -> str:
    root = repo_root.resolve()
    ps1 = root / "scripts" / "build_bundle_faiss_index.ps1"
    return f'powershell -NoProfile -ExecutionPolicy Bypass -File "{ps1}" -RepoRoot "{root}"'
