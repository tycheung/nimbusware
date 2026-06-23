from __future__ import annotations

import json
from collections import Counter, OrderedDict, UserDict, defaultdict
from dataclasses import dataclass
from types import MappingProxyType, SimpleNamespace

from nimbusware_api.routes.runs import (
    _finding_has_security_scan_metadata,
    security_scan_on_verify_timeline_summary,
)
from unit.composite_contract_fixtures import finding_dict_event

# Constants and tiny builder helpers

_EXIT_KEY = "security_scan_exit"
_SNIPPET_KEY = "security_scan_snippet"

_EXPECTED_SUMMARY_KEYS = {
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
}


# Part A -- _finding_has_security_scan_metadata isinstance / subclass matrix


class TestPartAIsinstanceSubclassMatrix:
    """``isinstance(meta, dict)`` is type-hierarchy-strict, not duck-typed."""

    def test_a1_ordered_dict_accepted_as_dict_subclass(self) -> None:
        meta = OrderedDict({_EXIT_KEY: 0})
        assert isinstance(meta, dict)
        assert _finding_has_security_scan_metadata(meta) is True

        # Also confirm with ordering preserved (the whole point of OrderedDict).
        meta_ordered = OrderedDict([("noise", 1), (_SNIPPET_KEY, "ok")])
        assert _finding_has_security_scan_metadata(meta_ordered) is True

    def test_a2_defaultdict_and_counter_accepted_as_dict_subclasses(self) -> None:
        dd = defaultdict(list, {_SNIPPET_KEY: "..."})
        assert isinstance(dd, dict)
        assert _finding_has_security_scan_metadata(dd) is True

        ct = Counter({_EXIT_KEY: 1})
        assert isinstance(ct, dict)
        assert _finding_has_security_scan_metadata(ct) is True

    def test_a3_user_dict_and_mapping_proxy_rejected_key_divergence(self) -> None:
        # UserDict: defines __contains__ via composition but is NOT a dict subclass.
        ud = UserDict({_EXIT_KEY: 1})
        assert not isinstance(ud, dict), (
            "UserDict is NOT a dict subclass -- pinning this assumption"
        )
        assert _EXIT_KEY in ud, "UserDict still supports `in` via __contains__"
        # ...but the guard rejects it because of isinstance over duck-typing.
        assert _finding_has_security_scan_metadata(ud) is False

        # MappingProxyType: read-only dict view, NOT a dict subclass.
        mp = MappingProxyType({_EXIT_KEY: 1})
        assert not isinstance(mp, dict)
        assert _EXIT_KEY in mp
        assert _finding_has_security_scan_metadata(mp) is False

    def test_a4_simple_namespace_and_dataclass_rejected(self) -> None:
        ns = SimpleNamespace(security_scan_exit=1, security_scan_snippet="...")
        assert not isinstance(ns, dict)
        assert _finding_has_security_scan_metadata(ns) is False

        @dataclass
        class _FakeMeta:
            security_scan_exit: int = 1
            security_scan_snippet: str = "..."

        fm = _FakeMeta()
        assert not isinstance(fm, dict)
        assert _finding_has_security_scan_metadata(fm) is False

    def test_a5_custom_contains_class_rejected_and_dict_subclass_honors_override(
        self,
    ) -> None:

        class HasContainsOnly:
            def __contains__(self, key: object) -> bool:
                return True

            def __iter__(self):
                return iter([])

        hco = HasContainsOnly()
        assert not isinstance(hco, dict)
        assert _EXIT_KEY in hco  # would-be duck-type happy
        assert _finding_has_security_scan_metadata(hco) is False

        class DictSubWithFalseContains(dict):
            def __contains__(self, key: object) -> bool:
                return False

        dsub = DictSubWithFalseContains({_EXIT_KEY: 1, _SNIPPET_KEY: "..."})
        assert isinstance(dsub, dict)
        # The dict literal physically contains the keys (via dict.keys),
        # but the override returns False for `in`.
        assert _EXIT_KEY in dsub.keys()
        assert _EXIT_KEY not in dsub  # override wins for `in`
        # The helper uses `in meta`, which respects the override -> False.
        assert _finding_has_security_scan_metadata(dsub) is False


# Part B -- _finding_has_security_scan_metadata exact-key matching matrix


class TestPartBExactKeyMatchingMatrix:
    """``in dict`` is case-sensitive, exact-match, and checks KEYS."""

    def test_b1_case_sensitivity_key_divergence(self) -> None:
        assert _finding_has_security_scan_metadata({"SECURITY_SCAN_EXIT": 1}) is False
        assert _finding_has_security_scan_metadata({"Security_Scan_Snippet": ""}) is False
        assert _finding_has_security_scan_metadata({"security_scan_EXIT": 1}) is False

        # Paired happy arm: exact lowercase succeeds.
        assert _finding_has_security_scan_metadata({_EXIT_KEY: 1}) is True

    def test_b2_typo_and_whitespace_key_variants_rejected(self) -> None:
        assert _finding_has_security_scan_metadata({"security_scan_exits": 1}) is False
        assert _finding_has_security_scan_metadata({"security_scan_snippe": "..."}) is False
        assert _finding_has_security_scan_metadata({" security_scan_exit": 1}) is False
        assert _finding_has_security_scan_metadata({"security_scan_exit ": 1}) is False
        assert _finding_has_security_scan_metadata({"\tsecurity_scan_exit": 1}) is False

    def test_b3_both_keys_present_with_falsy_values(self) -> None:
        meta = {_EXIT_KEY: 0, _SNIPPET_KEY: ""}
        assert _finding_has_security_scan_metadata(meta) is True

        # And with one None value too.
        meta_none = {_EXIT_KEY: None, _SNIPPET_KEY: None}
        assert _finding_has_security_scan_metadata(meta_none) is True

    def test_b4_key_as_value_rejection_key_divergence(self) -> None:
        bad = {"foo": _EXIT_KEY, "bar": _SNIPPET_KEY}
        assert _finding_has_security_scan_metadata(bad) is False

        # And the symmetric "both" case.
        bad_both = {
            "key1": _EXIT_KEY,
            "key2": _SNIPPET_KEY,
            "noise": [_EXIT_KEY, _SNIPPET_KEY],
        }
        assert _finding_has_security_scan_metadata(bad_both) is False

    def test_b5_extra_unrelated_keys_tolerated(self) -> None:
        meta = {
            _EXIT_KEY: 0,
            "noise_a": [1, 2, 3],
            "noise_b": object(),
            "_internal": None,
            "complex_object": {"nested": True},
        }
        assert _finding_has_security_scan_metadata(meta) is True


# Part C -- security_scan_on_verify_timeline_summary ordering / filtering


class TestPartCSummaryOrderingFiltering:
    """Loop behavior, event-type filter, ordering, and no-category-gate."""

    def test_c1_empty_input_returns_none(self) -> None:
        assert security_scan_on_verify_timeline_summary([]) is None

    def test_c2_list_order_ordering_not_timestamp_key_divergence(self) -> None:
        events = [
            finding_dict_event(
                event_id="ev-LATER-OCCURRED",
                occurred_at="2099-01-01T00:00:00Z",
                metadata={_EXIT_KEY: 0, _SNIPPET_KEY: "first"},
                payload={"finding_id": "f-FIRST"},
            ),
            finding_dict_event(
                event_id="ev-EARLIER-OCCURRED",
                occurred_at="1999-01-01T00:00:00Z",
                metadata={_EXIT_KEY: 1, _SNIPPET_KEY: "second"},
                payload={"finding_id": "f-SECOND"},
            ),
        ]
        result = security_scan_on_verify_timeline_summary(events)
        assert result is not None
        # Last-in-list wins even though its occurred_at is earlier.
        assert result["event_id"] == "ev-EARLIER-OCCURRED"
        assert result["occurred_at"] == "1999-01-01T00:00:00Z"
        assert result["finding_id"] == "f-SECOND"
        assert result["security_scan_snippet"] == "second"
        assert result["security_scan_exit"] == 1

    def test_c3_broader_wrong_event_type_matrix(self) -> None:
        wrong_types = [
            "run.created",
            "run.escalated",
            "stage.passed",
            "stage.failed",
            "gate.decision.emitted",
            "finding.updated",
            "model.selected.primary",
        ]
        for et in wrong_types:
            events = [
                finding_dict_event(
                    event_type=et,
                    metadata={_EXIT_KEY: 0, _SNIPPET_KEY: "..."},
                    payload={"finding_id": "f-1"},
                )
            ]
            assert security_scan_on_verify_timeline_summary(events) is None, (
                f"event_type={et!r} should be filtered out"
            )

    def test_c4_mixed_pass_through_keeps_out_none(self) -> None:
        events = [
            finding_dict_event(event_id="ev-1", metadata={}, payload={"finding_id": "f-1"}),
            finding_dict_event(event_id="ev-2", metadata=None, payload={"finding_id": "f-2"}),
            finding_dict_event(
                event_id="ev-3",
                metadata={"other_key": "x", "another": 42},
                payload={"finding_id": "f-3"},
            ),
        ]
        assert security_scan_on_verify_timeline_summary(events) is None

    def test_c5_no_category_gate_at_summary_layer(self) -> None:
        for category in ["performance", "style", "lint", "unknown"]:
            events = [
                finding_dict_event(
                    metadata={_EXIT_KEY: 0},
                    payload={
                        "finding_id": "f-1",
                        "category": category,
                        "severity": "low",
                    },
                )
            ]
            result = security_scan_on_verify_timeline_summary(events)
            assert result is not None, f"category={category!r} should NOT prevent summary"
            assert result["category"] == category
            assert result["severity"] == "low"


# Part D -- payload / source / return-type matrix


class TestPartDPayloadSourceReturnType:
    """Payload coercion, source-split guard, top-level attribution, return type."""

    def test_d1_payload_none_coerced_to_empty_dict(self) -> None:
        events = [
            finding_dict_event(
                event_id="ev-1",
                occurred_at="2024-01-01T00:00:00Z",
                metadata={_EXIT_KEY: 0, _SNIPPET_KEY: "ok"},
                payload=None,
            )
        ]
        result = security_scan_on_verify_timeline_summary(events)
        assert result is not None
        assert result["finding_id"] is None
        assert result["category"] is None
        assert result["severity"] is None
        assert result["source_artifact"] is None
        # Metadata fields still populated.
        assert result["security_scan_exit"] == 0
        assert result["security_scan_snippet"] == "ok"
        # Top-level fields still populated.
        assert result["event_id"] == "ev-1"
        assert result["occurred_at"] == "2024-01-01T00:00:00Z"

    def test_d2_non_dict_payload_coerced_to_empty_dict(self) -> None:
        for bad_payload in ["not-a-dict", [1, 2, 3], 42, True]:
            events = [
                finding_dict_event(
                    metadata={_EXIT_KEY: 0},
                    payload=bad_payload,
                )
            ]
            result = security_scan_on_verify_timeline_summary(events)
            assert result is not None, f"payload={bad_payload!r} should still produce summary"
            assert result["finding_id"] is None
            assert result["category"] is None
            assert result["severity"] is None
            assert result["source_artifact"] is None
            # Metadata-derived keys still populated.
            assert result["security_scan_exit"] == 0

    def test_d3_source_split_guard_metadata_only_key_divergence(self) -> None:
        # Scan keys in payload only; metadata empty.
        events_payload_only = [
            finding_dict_event(
                metadata={},
                payload={
                    _EXIT_KEY: 1,
                    _SNIPPET_KEY: "scan-data-misrouted",
                    "finding_id": "f-1",
                },
            )
        ]
        assert security_scan_on_verify_timeline_summary(events_payload_only) is None

        # Same with metadata explicitly None.
        events_meta_none = [
            finding_dict_event(
                metadata=None,
                payload={_EXIT_KEY: 1, _SNIPPET_KEY: "..."},
            )
        ]
        assert security_scan_on_verify_timeline_summary(events_meta_none) is None

        # Same with metadata key missing entirely from the event dict.
        events_meta_missing = [
            {
                "event_type": "finding.created",
                "event_id": "ev-1",
                "occurred_at": "2024-01-01T00:00:00Z",
                "payload": {_EXIT_KEY: 1, _SNIPPET_KEY: "..."},
            }
        ]
        assert security_scan_on_verify_timeline_summary(events_meta_missing) is None

    def test_d4_top_level_event_id_and_occurred_at_attribution(self) -> None:
        events = [
            finding_dict_event(
                event_id="ev-TOP-LEVEL",
                occurred_at="2025-01-01T00:00:00Z",
                metadata={_EXIT_KEY: 0},
                payload={
                    "event_id": "ev-FROM-PAYLOAD",
                    "occurred_at": "2099-12-31T23:59:59Z",
                    "finding_id": "f-1",
                },
            )
        ]
        result = security_scan_on_verify_timeline_summary(events)
        assert result is not None
        # Top-level wins for these two keys.
        assert result["event_id"] == "ev-TOP-LEVEL"
        assert result["occurred_at"] == "2025-01-01T00:00:00Z"
        # finding_id, which is unambiguously payload-derived, comes from payload.
        assert result["finding_id"] == "f-1"

    def test_d5_return_type_is_plain_dict_key_divergence(self) -> None:
        events = [
            finding_dict_event(
                metadata={_EXIT_KEY: 0, _SNIPPET_KEY: "snippet-text"},
                payload={
                    "finding_id": "f-1",
                    "category": "security",
                    "severity": "high",
                    "source_artifact": "src/x.py",
                },
            )
        ]
        result = security_scan_on_verify_timeline_summary(events)
        assert result is not None
        # Plain dict -- NOT OrderedDict, NOT a custom subclass.
        assert type(result) is dict

        # Exact 10-key shape -- pins no accidental field additions/removals.
        assert set(result.keys()) == _EXPECTED_SUMMARY_KEYS
        assert len(result) == 10

        # JSON-serializable.
        encoded = json.dumps(result)
        decoded = json.loads(encoded)
        assert decoded == result

        # Mutable: callers may add keys without violating an immutable contract.
        result["caller_added"] = "extra"
        assert len(result) == 11
        assert result["caller_added"] == "extra"
