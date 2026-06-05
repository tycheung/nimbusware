from __future__ import annotations

import time
from pathlib import Path

from nimbusware_extensions.catalog import bundle_faiss_index_sync_state


def _touch(p: Path, *, age_sec: float = 0.0) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")
    if age_sec:
        t = time.time() - age_sec
        import os

        os.utime(p, (t, t))


def test_sync_state_no_index_stale_none(tmp_path: Path) -> None:
    cat = tmp_path / "configs" / "bundles" / "catalog.yaml"
    _touch(cat)
    s = bundle_faiss_index_sync_state(tmp_path)
    assert s["ready"] is False
    assert s["stale"] is None
    assert s["catalog_exists"] is True
    assert s["index_max_mtime_ns"] is None


def test_sync_state_ready_not_stale_when_index_newer(tmp_path: Path) -> None:
    cat = tmp_path / "configs" / "bundles" / "catalog.yaml"
    idx = tmp_path / "configs" / "bundles" / "index"
    _touch(cat, age_sec=100.0)
    _touch(idx / "faiss.index", age_sec=10.0)
    _touch(idx / "bundle_order.json", age_sec=10.0)
    s = bundle_faiss_index_sync_state(tmp_path)
    assert s["ready"] is True
    assert s["stale"] is False
    assert s["catalog_mtime_ns"] is not None
    assert s["index_max_mtime_ns"] is not None


def test_sync_state_stale_when_catalog_newer(tmp_path: Path) -> None:
    cat = tmp_path / "configs" / "bundles" / "catalog.yaml"
    idx = tmp_path / "configs" / "bundles" / "index"
    _touch(idx / "faiss.index", age_sec=100.0)
    _touch(idx / "bundle_order.json", age_sec=100.0)
    _touch(cat, age_sec=1.0)
    s = bundle_faiss_index_sync_state(tmp_path)
    assert s["ready"] is True
    assert s["stale"] is True
