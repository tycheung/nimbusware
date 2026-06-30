from __future__ import annotations

from typing import Any

from nimbusware_console.explainer_core.display_common import stringify_display_value as _stringify

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
