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

from nimbusware_console.bundle_catalog.catalog_local._cells import (
    _bundle_search_hit_cell,
)

def run_bundle_catalog_search(repo_root: Path, query: str, *, k: int) -> dict[str, Any]:
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
