from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from nimbusware_console.bundle_catalog.faiss_status._constants import (
    BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH,
)


def bundle_faiss_index_status_operator_metrics(
    status: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "ready": False,
        "stale": None,
        "faiss_index_exists": False,
        "bundle_order_exists": False,
    }
    if not isinstance(status, Mapping):
        return metrics
    if status.get("ready") is True:
        metrics["ready"] = True
    stale = status.get("stale")
    if isinstance(stale, bool):
        metrics["stale"] = stale
    if status.get("faiss_index_exists") is True:
        metrics["faiss_index_exists"] = True
    if status.get("bundle_order_exists") is True:
        metrics["bundle_order_exists"] = True
    return metrics


def bundle_faiss_index_status_operator_metrics_table_rows(
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


def bundle_faiss_index_status_operator_metrics_caption(
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


def bundle_faiss_index_workflow_caption_note() -> str:
    return (
        f"Weekly / manual smoke: repo file ``{BUNDLE_FAISS_INDEX_WORKFLOW_RELPATH}`` "
        "(workflow name **bundle_faiss_index**)."
    )


def bundle_faiss_build_command_snippet() -> str:
    return (
        "poetry install --with faiss\n"
        "poetry run python scripts/build_bundle_faiss_index.py\n"
        "# poetry run python scripts/build_bundle_faiss_index.py --help"
    )


def bundle_faiss_build_command_snippet_explicit(repo_root: Path) -> str:
    root_s = str(repo_root.resolve())
    return (
        "poetry install --with faiss\n"
        f'poetry run python scripts/build_bundle_faiss_index.py --repo-root "{root_s}"\n'
        "# poetry run python scripts/build_bundle_faiss_index.py --help"
    )


def bundle_faiss_build_powershell_snippet_explicit(repo_root: Path) -> str:
    root_s = str(repo_root.resolve())
    return (
        "poetry install --with faiss\n"
        f'poetry run python scripts/build_bundle_faiss_index.py --repo-root "{root_s}"\n'
        f'# Or: .\\scripts\\build_bundle_faiss_index.ps1 -RepoRoot "{root_s}"'
    )


def bundle_faiss_invoke_ps1_snippet_explicit(repo_root: Path) -> str:
    root = repo_root.resolve()
    ps1 = root / "scripts" / "build_bundle_faiss_index.ps1"
    return (
        f'powershell -NoProfile -ExecutionPolicy Bypass -File "{ps1}" '
        f'-RepoRoot "{root}"'
    )


