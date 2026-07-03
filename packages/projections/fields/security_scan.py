from __future__ import annotations

SECURITY_SCAN_ROW_KEYS: tuple[str, ...] = (
    "event_id",
    "occurred_at",
    "finding_id",
    "category",
    "severity",
    "source_artifact",
    "security_scan_exit",
    "security_scan_ruff_exit",
    "security_scan_bandit_exit",
    "security_scan_snippet",
)

__all__ = ["SECURITY_SCAN_ROW_KEYS"]
