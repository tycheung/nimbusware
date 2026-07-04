from __future__ import annotations

import hashlib
import json
from typing import Any


def memory_event_rows_fingerprint(rows: list[dict[str, Any]]) -> str:
    h = hashlib.sha256()
    for row in rows:
        h.update(str(row.get("store_seq")).encode("utf-8"))
        h.update(b"\0")
        h.update(str(row.get("event_type")).encode("utf-8"))
        h.update(b"\0")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        h.update(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))
        h.update(b"\0")
    return h.hexdigest()
