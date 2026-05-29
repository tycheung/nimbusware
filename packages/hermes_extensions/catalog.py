"""Bundle catalog (plan §3A, §14 #12) with tag search + optional on-disk FAISS index.

Use :func:`search_bundles` for a repo-root-relative catalog search without constructing
paths at the call site.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from hermes_orchestrator.merge import load_yaml


def assert_workflow_bundle_map_ids_resolve_content(raw: dict[str, Any]) -> None:
    """Raise if ``workflow_bundle_map`` references bundle ids missing from ``bundles``."""
    bundles = raw.get("bundles")
    if not isinstance(bundles, list):
        known: set[str] = set()
    else:
        known = {
            str(b.get("id")).strip()
            for b in bundles
            if isinstance(b, dict) and b.get("id") is not None and str(b.get("id")).strip()
        }
    wmap = raw.get("workflow_bundle_map")
    if not isinstance(wmap, dict) or not wmap:
        return
    errors: list[str] = []
    for wf_prof, mapped in wmap.items():
        bid = str(mapped).strip() if mapped is not None else ""
        if not bid:
            errors.append(f"workflow_bundle_map[{wf_prof!r}] is empty or null")
            continue
        if bid not in known:
            errors.append(f"workflow_bundle_map[{wf_prof!r}] -> unknown bundle id {bid!r}")
    if errors:
        msg = "; ".join(errors[:10])
        if len(errors) > 10:
            msg += f"; (+{len(errors) - 10} more)"
        raise ValueError(f"bundle catalog workflow_bundle_map: {msg}")


def assert_workflow_bundle_map_ids_resolve(catalog_path: Path) -> None:
    """Raise if ``workflow_bundle_map`` references bundle ids missing from ``bundles`` (§14 #12)."""
    if not catalog_path.is_file():
        raise FileNotFoundError(f"missing bundle catalog: {catalog_path}")
    raw = load_yaml(catalog_path)
    assert_workflow_bundle_map_ids_resolve_content(raw)


def validate_bundle_catalog_content(raw: dict[str, Any]) -> None:
    """Structural validation before persisting bundle catalog edits (§14 #12)."""
    if not isinstance(raw, dict):
        raise ValueError("bundle catalog must be a mapping")
    bundles = raw.get("bundles")
    if bundles is None:
        return
    if not isinstance(bundles, list):
        raise ValueError("bundles must be a list")
    seen: set[str] = set()
    for i, b in enumerate(bundles):
        if not isinstance(b, dict):
            raise ValueError(f"bundles[{i}] must be a mapping")
        bid_raw = b.get("id")
        if bid_raw is None or not str(bid_raw).strip():
            raise ValueError(f"bundles[{i}].id is required")
        bid = str(bid_raw).strip()
        if bid in seen:
            raise ValueError(f"duplicate bundle id {bid!r}")
        seen.add(bid)
    wmap = raw.get("workflow_bundle_map")
    if wmap is not None and not isinstance(wmap, dict):
        raise ValueError("workflow_bundle_map must be a mapping when present")
    assert_workflow_bundle_map_ids_resolve_content(raw)


class BundleCatalog:
    """Load bundle metadata from YAML; optional FAISS index under ``index_dir``."""

    def __init__(self, catalog_path: Path, *, index_dir: Path | None = None) -> None:
        self._raw = load_yaml(catalog_path)
        self._index_dir = index_dir or (catalog_path.parent / "index")
        self._faiss = self._try_load_faiss()

    def list_bundles(self) -> list[dict[str, Any]]:
        bundles = self._raw.get("bundles")
        if not isinstance(bundles, list):
            return []
        return [b for b in bundles if isinstance(b, dict)]

    def embed_query(self, text: str) -> NDArray[np.float32]:
        """Deterministic pseudo-embedding (matches ``scripts/build_bundle_faiss_index``)."""
        h = hashlib.sha256(text.encode()).digest()
        vec = np.frombuffer(h[:32], dtype=np.uint8).astype(np.float32)
        n = float(np.linalg.norm(vec)) + 1e-9
        return vec / n

    def _try_load_faiss(self) -> tuple[Any, list[str]] | None:
        idx_path = self._index_dir / "faiss.index"
        meta_path = self._index_dir / "bundle_order.json"
        if not idx_path.is_file() or not meta_path.is_file():
            return None
        try:
            import faiss  # type: ignore[import-not-found]
        except ImportError:
            return None
        index = faiss.read_index(str(idx_path))
        bundle_order: list[str] = json.loads(meta_path.read_text(encoding="utf-8"))
        return (index, bundle_order)

    def _search_tags(self, query: str, *, k: int) -> list[dict[str, Any]]:
        terms = {t.lower() for t in query.replace(",", " ").split() if t.strip()}
        bundles = self.list_bundles()
        ranked: list[tuple[float, dict[str, Any]]] = []
        for b in bundles:
            bid = str(b.get("id", "")).lower()
            tags = {str(x).lower() for x in (b.get("tags") or []) if isinstance(x, str)}
            score = float(sum(1 for t in terms if t in tags or t in bid))
            ranked.append((score, b))
        ranked.sort(key=lambda x: x[0], reverse=True)
        if not ranked:
            return []
        if ranked[0][0] == 0.0:
            return [b for _, b in ranked[:k]]
        return [b for s, b in ranked[:k] if s > 0]

    def search(self, query: str, *, k: int = 5) -> list[dict[str, Any]]:
        """Prefer FAISS top-``k`` when an index is present; otherwise tag/id overlap."""
        if self._faiss is not None:
            index, order = self._faiss
            q = self.embed_query(query).reshape(1, -1).astype(np.float32)
            _, inds = index.search(q, min(k, len(order)))
            bundles_by_id = {str(b.get("id")): b for b in self.list_bundles()}
            out: list[dict[str, Any]] = []
            for i in inds[0]:
                if int(i) < 0 or int(i) >= len(order):
                    continue
                bid = order[int(i)]
                b = bundles_by_id.get(bid)
                if b:
                    out.append(b)
            if out:
                return out[:k]
        return self._search_tags(query, k=k)


def search_bundles_raw(raw: dict[str, Any], query: str, *, k: int = 5) -> list[dict[str, Any]]:
    """Search against a preloaded bundle-catalog mapping."""
    terms = {t.lower() for t in query.replace(",", " ").split() if t.strip()}
    bundles_raw = raw.get("bundles")
    bundles = bundles_raw if isinstance(bundles_raw, list) else []
    ranked: list[tuple[float, dict[str, Any]]] = []
    for b in bundles:
        if not isinstance(b, dict):
            continue
        bid = str(b.get("id", "")).lower()
        tags = {str(x).lower() for x in (b.get("tags") or []) if isinstance(x, str)}
        score = float(sum(1 for t in terms if t in tags or t in bid))
        ranked.append((score, b))
    ranked.sort(key=lambda x: x[0], reverse=True)
    if not ranked:
        return []
    if ranked[0][0] == 0.0:
        return [b for _, b in ranked[: max(1, int(k))]]
    return [b for s, b in ranked[: max(1, int(k))] if s > 0]


def load_bundle_catalog_content(
    repo_root: Path,
    *,
    config_materializer: Any | None = None,
) -> dict[str, Any] | None:
    """Load bundle catalog from DB-backed materializer or on-disk YAML."""
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        try:
            raw = config_materializer.get_bundle_catalog()
        except (AttributeError, KeyError):
            return None
        return raw if isinstance(raw, dict) else None
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if not path.is_file():
        return None
    return load_yaml(path)


def search_bundles(
    repo_root: Path,
    query: str,
    *,
    k: int = 5,
    config_materializer: Any | None = None,
) -> list[dict[str, Any]]:
    """Operator helper: tag/id search over ``{repo_root}/configs/bundles/catalog.yaml``.

    Returns ``[]`` when the catalog file is missing. Otherwise delegates to
    :class:`BundleCatalog` (FAISS when an index is present under ``bundles/index/``,
    else tag overlap — same semantics as :meth:`BundleCatalog.search`).
    """
    raw = load_bundle_catalog_content(repo_root, config_materializer=config_materializer)
    if raw is None:
        return []
    path = repo_root / "configs" / "bundles" / "catalog.yaml"
    if config_materializer is not None and getattr(config_materializer, "use_db", False):
        return search_bundles_raw(raw, query.strip(), k=k)
    return BundleCatalog(path).search(query.strip(), k=k)


def bundle_faiss_index_ready(repo_root: Path) -> bool:
    """Return ``True`` when both bundle FAISS index files exist under ``repo_root``.

    Checks ``configs/bundles/index/faiss.index`` and ``configs/bundles/index/bundle_order.json``
    (the two files written by ``scripts/build_bundle_faiss_index.py`` and consumed by
    :meth:`BundleCatalog._try_load_faiss`). This is a *file-presence* signal only — it does
    not import ``faiss`` or attempt to load the index, so it stays cheap to call from API
    handlers and Streamlit captions alike.
    """
    idx_dir = repo_root / "configs" / "bundles" / "index"
    return (idx_dir / "faiss.index").is_file() and (idx_dir / "bundle_order.json").is_file()


def bundle_faiss_index_sync_state(repo_root: Path) -> dict[str, Any]:
    """Cheap index vs catalog mtimes for operators (PLAN_GAP §14 #12).

    ``stale`` is ``True`` when both index files exist, the catalog file exists, and the
    catalog's mtime is newer than the newer of the two index files — a rebuild is likely
    needed. ``None`` when the index is incomplete, the catalog is missing, or freshness
    cannot be compared.
    """
    cat = repo_root / "configs" / "bundles" / "catalog.yaml"
    idx_dir = repo_root / "configs" / "bundles" / "index"
    faiss_p = idx_dir / "faiss.index"
    meta_p = idx_dir / "bundle_order.json"
    ready = faiss_p.is_file() and meta_p.is_file()
    out: dict[str, Any] = {
        "catalog_path": str(cat.resolve()) if cat.is_file() else str(cat),
        "catalog_exists": cat.is_file(),
        "ready": ready,
    }
    if not ready:
        out["stale"] = None
        out["index_max_mtime_ns"] = None
        out["catalog_mtime_ns"] = (
            int(cat.stat().st_mtime_ns) if cat.is_file() else None
        )
        return out
    idx_m = max(int(faiss_p.stat().st_mtime_ns), int(meta_p.stat().st_mtime_ns))
    out["index_max_mtime_ns"] = idx_m
    if not cat.is_file():
        out["stale"] = None
        out["catalog_mtime_ns"] = None
        return out
    cm = int(cat.stat().st_mtime_ns)
    out["catalog_mtime_ns"] = cm
    out["catalog_path"] = str(cat.resolve())
    out["stale"] = cm > idx_m
    return out
