from __future__ import annotations

from typing import Any

EXIT_KEY = "security_scan_exit"
SNIPPET_KEY = "security_scan_snippet"

EXPECTED_SUMMARY_KEYS = frozenset(
    {
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
    },
)

FINDING_HAS_METADATA_CASES: tuple[dict[str, Any], ...] = (
    {"case_id": "case_upper_exit", "meta": {"SECURITY_SCAN_EXIT": 1}, "expected": False},
    {"case_id": "case_upper_snippet", "meta": {"Security_Scan_Snippet": ""}, "expected": False},
    {"case_id": "case_mixed_case", "meta": {"security_scan_EXIT": 1}, "expected": False},
    {"case_id": "exact_exit", "meta": {EXIT_KEY: 1}, "expected": True},
    {"case_id": "typo_exits", "meta": {"security_scan_exits": 1}, "expected": False},
    {"case_id": "typo_snippe", "meta": {"security_scan_snippe": "..."}, "expected": False},
    {"case_id": "ws_prefix", "meta": {" security_scan_exit": 1}, "expected": False},
    {"case_id": "ws_suffix", "meta": {"security_scan_exit ": 1}, "expected": False},
    {"case_id": "tab_prefix", "meta": {"\tsecurity_scan_exit": 1}, "expected": False},
    {
        "case_id": "both_falsy",
        "meta": {EXIT_KEY: 0, SNIPPET_KEY: ""},
        "expected": True,
    },
    {
        "case_id": "both_none",
        "meta": {EXIT_KEY: None, SNIPPET_KEY: None},
        "expected": True,
    },
    {"case_id": "key_as_value", "meta": {"foo": EXIT_KEY, "bar": SNIPPET_KEY}, "expected": False},
    {
        "case_id": "extra_keys",
        "meta": {EXIT_KEY: 0, "noise_a": [1, 2], "noise_b": object(), "_internal": None},
        "expected": True,
    },
)

WRONG_EVENT_TYPES: tuple[str, ...] = (
    "run.created",
    "run.escalated",
    "stage.passed",
    "stage.failed",
    "gate.decision.emitted",
    "finding.updated",
    "model.selected.primary",
)

SUMMARY_CATEGORY_CASES: tuple[str, ...] = ("performance", "style", "lint", "unknown")

BAD_PAYLOAD_VALUES: tuple[Any, ...] = ("not-a-dict", [1, 2, 3], 42, True)
