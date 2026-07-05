from __future__ import annotations

import json
from collections import Counter, OrderedDict, UserDict, defaultdict
from dataclasses import dataclass
from types import MappingProxyType, SimpleNamespace

import pytest

from api.routes.runs import (
    _finding_has_security_scan_metadata,
    security_scan_on_verify_timeline_summary,
)
from unit.composite_contract_fixtures import finding_dict_event
from unit.composite_contracts.security_scan_metadata_matrix import (
    BAD_PAYLOAD_VALUES,
    EXIT_KEY,
    EXPECTED_SUMMARY_KEYS,
    FINDING_HAS_METADATA_CASES,
    SNIPPET_KEY,
    SUMMARY_CATEGORY_CASES,
    WRONG_EVENT_TYPES,
)


class TestPartAIsinstanceSubclassMatrix:
    def test_dict_subclasses_accepted(self) -> None:
        assert _finding_has_security_scan_metadata(OrderedDict({EXIT_KEY: 0})) is True
        assert _finding_has_security_scan_metadata(defaultdict(list, {SNIPPET_KEY: "..."})) is True
        assert _finding_has_security_scan_metadata(Counter({EXIT_KEY: 1})) is True

    def test_non_dict_types_rejected(self) -> None:
        ud = UserDict({EXIT_KEY: 1})
        assert _finding_has_security_scan_metadata(ud) is False
        assert _finding_has_security_scan_metadata(MappingProxyType({EXIT_KEY: 1})) is False
        assert (
            _finding_has_security_scan_metadata(
                SimpleNamespace(security_scan_exit=1, security_scan_snippet="..."),
            )
            is False
        )

        @dataclass
        class _FakeMeta:
            security_scan_exit: int = 1
            security_scan_snippet: str = "..."

        assert _finding_has_security_scan_metadata(_FakeMeta()) is False

    def test_contains_override_honored(self) -> None:
        class DictSubWithFalseContains(dict):
            def __contains__(self, key: object) -> bool:
                return False

        dsub = DictSubWithFalseContains({EXIT_KEY: 1, SNIPPET_KEY: "..."})
        assert _finding_has_security_scan_metadata(dsub) is False


@pytest.mark.parametrize("case", FINDING_HAS_METADATA_CASES, ids=lambda c: c["case_id"])
def test_finding_has_security_scan_metadata_key_matrix(case: dict) -> None:
    assert _finding_has_security_scan_metadata(case["meta"]) is case["expected"]


def test_summary_empty_input_returns_none() -> None:
    assert security_scan_on_verify_timeline_summary([]) is None


def test_summary_list_order_wins_over_timestamp() -> None:
    events = [
        finding_dict_event(
            event_id="ev-LATER",
            occurred_at="2099-01-01T00:00:00Z",
            metadata={EXIT_KEY: 0, SNIPPET_KEY: "first"},
            payload={"finding_id": "f-FIRST"},
        ),
        finding_dict_event(
            event_id="ev-EARLIER",
            occurred_at="1999-01-01T00:00:00Z",
            metadata={EXIT_KEY: 1, SNIPPET_KEY: "second"},
            payload={"finding_id": "f-SECOND"},
        ),
    ]
    result = security_scan_on_verify_timeline_summary(events)
    assert result is not None
    assert result["event_id"] == "ev-EARLIER"
    assert result["finding_id"] == "f-SECOND"


@pytest.mark.parametrize("event_type", WRONG_EVENT_TYPES)
def test_summary_filters_wrong_event_types(event_type: str) -> None:
    events = [
        finding_dict_event(
            event_type=event_type,
            metadata={EXIT_KEY: 0, SNIPPET_KEY: "..."},
            payload={"finding_id": "f-1"},
        ),
    ]
    assert security_scan_on_verify_timeline_summary(events) is None


def test_summary_mixed_pass_through_returns_none() -> None:
    events = [
        finding_dict_event(event_id="ev-1", metadata={}, payload={"finding_id": "f-1"}),
        finding_dict_event(event_id="ev-2", metadata=None, payload={"finding_id": "f-2"}),
    ]
    assert security_scan_on_verify_timeline_summary(events) is None


@pytest.mark.parametrize("category", SUMMARY_CATEGORY_CASES)
def test_summary_no_category_gate(category: str) -> None:
    events = [
        finding_dict_event(
            metadata={EXIT_KEY: 0},
            payload={"finding_id": "f-1", "category": category, "severity": "low"},
        ),
    ]
    result = security_scan_on_verify_timeline_summary(events)
    assert result is not None
    assert result["category"] == category


def test_summary_payload_none_coerced() -> None:
    result = security_scan_on_verify_timeline_summary(
        [
            finding_dict_event(
                metadata={EXIT_KEY: 0, SNIPPET_KEY: "ok"},
                payload=None,
            ),
        ],
    )
    assert result is not None
    assert result["finding_id"] is None
    assert result["security_scan_exit"] == 0


@pytest.mark.parametrize("bad_payload", BAD_PAYLOAD_VALUES)
def test_summary_non_dict_payload_coerced(bad_payload: object) -> None:
    result = security_scan_on_verify_timeline_summary(
        [finding_dict_event(metadata={EXIT_KEY: 0}, payload=bad_payload)],
    )
    assert result is not None
    assert result["finding_id"] is None


def test_summary_metadata_only_scan_keys_rejected() -> None:
    assert (
        security_scan_on_verify_timeline_summary(
            [
                finding_dict_event(
                    metadata={},
                    payload={EXIT_KEY: 1, SNIPPET_KEY: "x", "finding_id": "f-1"},
                ),
            ],
        )
        is None
    )


def test_summary_top_level_id_wins() -> None:
    result = security_scan_on_verify_timeline_summary(
        [
            finding_dict_event(
                event_id="ev-TOP",
                occurred_at="2025-01-01T00:00:00Z",
                metadata={EXIT_KEY: 0},
                payload={"event_id": "ev-PAYLOAD", "finding_id": "f-1"},
            ),
        ],
    )
    assert result is not None
    assert result["event_id"] == "ev-TOP"
    assert result["finding_id"] == "f-1"


def test_summary_return_plain_dict_ten_keys() -> None:
    result = security_scan_on_verify_timeline_summary(
        [
            finding_dict_event(
                metadata={EXIT_KEY: 0, SNIPPET_KEY: "snippet-text"},
                payload={
                    "finding_id": "f-1",
                    "category": "security",
                    "severity": "high",
                    "source_artifact": "src/x.py",
                },
            ),
        ],
    )
    assert result is not None
    assert type(result) is dict
    assert set(result.keys()) == EXPECTED_SUMMARY_KEYS
    assert json.loads(json.dumps(result)) == result
