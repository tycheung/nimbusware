from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from io import StringIO
from typing import Any

# Order matches ``security_scan_on_verify_timeline_summary`` in runs (scan first).
_SECURITY_SCAN_ON_VERIFY_FIELDS: tuple[tuple[str, str], ...] = (
    ("security_scan_exit", "Security scan exit"),
    ("security_scan_ruff_exit", "Ruff exit"),
    ("security_scan_bandit_exit", "Bandit exit"),
    ("security_scan_snippet", "Security scan snippet"),
    ("category", "Category"),
    ("severity", "Severity"),
    ("source_artifact", "Source artifact"),
    ("finding_id", "Finding id"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)


def _stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)

