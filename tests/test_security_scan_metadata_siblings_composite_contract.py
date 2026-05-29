"""Security-scan metadata sibling helpers composite.

``_finding_has_security_scan_metadata`` +
``security_scan_on_verify_timeline_summary`` sibling composite.

Two paired helpers in
[packages/nimbusware_api/routes/runs.py](packages/nimbusware_api/routes/runs.py)
(lines 158-187) shape the ``GET /v1/runs/{run_id}/timeline``
``security_scan_on_verify`` field. fo112 Part D already pinned 5 axes
(generic non-dict guard, OR/``in`` value semantics, ``stage.started``
event_type filter, 8-key happy path, latest-wins ordering). fo121
extends with **20 NET-NEW** axes covering the four sharpest unpinned
surfaces:

* **Part A** -- ``_finding_has_security_scan_metadata`` isinstance /
 subclass matrix (5 axes): ``OrderedDict`` / ``defaultdict`` /
 ``Counter`` accepted (dict subclasses), **``collections.UserDict``**
 / **``types.MappingProxyType``** REJECTED (composition-based wrappers
 / read-only views that are NOT ``dict`` subclasses -- KEY DIVERGENCE
 against duck typing), ``SimpleNamespace`` and dataclass rejected,
 custom ``__contains__`` class rejected (isinstance over
 duck-typing), and a paired dict-subclass with overridden
 ``__contains__`` honoring the override.
* **Part B** -- exact-key matching matrix (5 axes): case sensitivity
 (KEY DIVERGENCE), typo / whitespace variants, BOTH keys present with
 falsy values, key-as-VALUE rejection (``in dict`` checks KEYS, not
 values -- KEY DIVERGENCE), extra unrelated keys tolerated.
* **Part C** -- summary ordering / filtering matrix (5 axes): empty
 input list, list-order ordering NOT timestamp-order (KEY
 DIVERGENCE), broader wrong-event-type matrix (run.created,
 run.escalated, stage.passed, gate.decision.emitted, finding.updated),
 mixed pass-through where guard fails on every event, no category
 gate at this layer.
* **Part D** -- payload / source / return-type matrix (5 axes):
 ``payload=None`` coercion, non-dict payload (string / list) coercion
 to ``pl == {}``, source-split guard checks metadata ONLY (KEY
 DIVERGENCE), top-level ``event_id`` / ``occurred_at`` from event NOT
 payload, return type is plain ``dict`` -- not ``TypedDict``, not
 dataclass, mutable and ``json.dumps``-serializable (KEY DIVERGENCE).

KEY DIVERGENCES pinned across the composite:

* **``isinstance(meta, dict)`` over duck-typing** -- ``UserDict`` /
 ``MappingProxyType`` REJECTED despite being "dict-like." A refactor
 to ``isinstance(meta, collections.abc.Mapping)`` would silently
 accept them.
* **Case-sensitive key matching** -- ``"SECURITY_SCAN_EXIT"`` NOT
 matched. A refactor to ``k.lower() in {...}`` would silently accept.
* **``in dict`` checks KEYS, not values** -- a refactor to
 ``... in meta.values()`` would invert the contract.
* **List-order ordering, NOT timestamp-order** -- LAST list match wins
 regardless of ``occurred_at``. A refactor to
 ``sorted(events, key=lambda e: e["occurred_at"])[-1]`` would change
 semantics for un-sorted input.
* **Source-split guard** -- guard checks ``meta`` only; scan keys
 living in ``payload`` do NOT surface a summary.
* **Plain ``dict`` return type** -- not ``TypedDict``, not dataclass.
 A future refactor to a frozen dataclass would break callers that
 mutate / ``json.dumps`` the result.

All tests call the two helpers **directly** with hand-built event
dicts. No FastAPI ``TestClient``, no fixtures beyond pytest built-ins,
no mocks.
"""

from __future__ import annotations

import json
from collections import Counter, OrderedDict, UserDict, defaultdict
from dataclasses import dataclass
from types import MappingProxyType, SimpleNamespace
from typing import Any

from nimbusware_api.routes.runs import (
    _finding_has_security_scan_metadata,
    security_scan_on_verify_timeline_summary,
)

# ---------------------------------------------------------------------------
# Constants and tiny builder helpers
# ---------------------------------------------------------------------------

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


def _finding_event(
    *,
    event_id: str = "ev-1",
    occurred_at: str = "2024-01-01T00:00:00Z",
    metadata: Any = None,
    payload: Any = None,
    event_type: str = "finding.created",
) -> dict[str, Any]:
    """Build a minimal ``finding.created`` event dict for the summary helper."""
    return {
        "event_type": event_type,
        "event_id": event_id,
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


# ===========================================================================
# Part A -- _finding_has_security_scan_metadata isinstance / subclass matrix
# ===========================================================================


class TestPartAIsinstanceSubclassMatrix:
    """``isinstance(meta, dict)`` is type-hierarchy-strict, not duck-typed."""

    def test_a1_ordered_dict_accepted_as_dict_subclass(self) -> None:
        """A1: ``OrderedDict`` is a ``dict`` subclass -- guard accepts it.

        fo112 D1 covers only "obviously-not-dict" shapes. ``OrderedDict``
        is the most common ordered-mapping type in the standard library
        and inherits directly from ``dict``, so ``isinstance(_, dict)``
        is ``True``.
        """
        meta = OrderedDict({_EXIT_KEY: 0})
        assert isinstance(meta, dict)
        assert _finding_has_security_scan_metadata(meta) is True

        # Also confirm with ordering preserved (the whole point of OrderedDict).
        meta_ordered = OrderedDict([("noise", 1), (_SNIPPET_KEY, "ok")])
        assert _finding_has_security_scan_metadata(meta_ordered) is True

    def test_a2_defaultdict_and_counter_accepted_as_dict_subclasses(self) -> None:
        """A2: ``defaultdict`` and ``Counter`` are ``dict`` subclasses too.

        Even with non-trivial factories (``defaultdict(list)``) or
        custom update semantics (``Counter``), both still inherit from
        ``dict`` and pass the guard.
        """
        dd = defaultdict(list, {_SNIPPET_KEY: "..."})
        assert isinstance(dd, dict)
        assert _finding_has_security_scan_metadata(dd) is True

        ct = Counter({_EXIT_KEY: 1})
        assert isinstance(ct, dict)
        assert _finding_has_security_scan_metadata(ct) is True

    def test_a3_user_dict_and_mapping_proxy_rejected_key_divergence(self) -> None:
        """A3: ``UserDict`` and ``MappingProxyType`` REJECTED (KEY DIVERGENCE).

        ``collections.UserDict`` is a composition-based wrapper -- it
        stores its data in a ``.data`` attribute and does NOT inherit
        from ``dict``. ``types.MappingProxyType`` is a read-only view
        and also NOT a ``dict`` subclass. Both implement
        ``__contains__`` and would pass a duck-typed check. A refactor
        to ``isinstance(meta, collections.abc.Mapping)`` would silently
        accept both.
        """
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
        """A4: attribute-based "duck-typed metadata" is not accepted.

        ``types.SimpleNamespace`` and ordinary ``@dataclass`` instances
        expose fields via attributes, not via ``__contains__``. Even if
        a caller accidentally passed one, the guard correctly rejects.
        """
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
        """A5: isinstance over duck-typing (KEY DIVERGENCE), plus override-respect.

        First arm: a class that implements ``__contains__`` returning
        ``True`` for everything still REJECTED because it is not a
        ``dict`` subclass. A refactor that pre-tested
        ``hasattr(meta, "__contains__")`` would silently accept this.

        Second arm: a ``dict`` SUBCLASS that overrides ``__contains__``
        to always return ``False`` still passes the ``isinstance`` guard
        (it IS a dict subclass), and then the ``in`` check correctly
        defers to the override -- so the result is ``False`` even
        though the dict literal contains the scan key. Pins that the
        guard does NOT bypass ``__contains__``; it uses standard ``in``.
        """

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
        # The dict literal physically contains the keys (via dict.keys()),
        # but the override returns False for `in`.
        assert _EXIT_KEY in dsub.keys()
        assert _EXIT_KEY not in dsub  # override wins for `in`
        # The helper uses `in meta`, which respects the override -> False.
        assert _finding_has_security_scan_metadata(dsub) is False


# ===========================================================================
# Part B -- _finding_has_security_scan_metadata exact-key matching matrix
# ===========================================================================


class TestPartBExactKeyMatchingMatrix:
    """``in dict`` is case-sensitive, exact-match, and checks KEYS."""

    def test_b1_case_sensitivity_key_divergence(self) -> None:
        """B1: KEY DIVERGENCE -- ``in`` is case-sensitive.

        ``"SECURITY_SCAN_EXIT"`` (all upper) and ``"Security_Scan_Snippet"``
        (mixed) do NOT match the lowercase keys looked for by the guard.
        A refactor to ``any(k.lower() in {...} for k in meta)`` would
        silently accept these. Paired happy: the canonical lowercase
        key matches.
        """
        assert _finding_has_security_scan_metadata({"SECURITY_SCAN_EXIT": 1}) is False
        assert (
            _finding_has_security_scan_metadata({"Security_Scan_Snippet": ""}) is False
        )
        assert _finding_has_security_scan_metadata({"security_scan_EXIT": 1}) is False

        # Paired happy arm: exact lowercase succeeds.
        assert _finding_has_security_scan_metadata({_EXIT_KEY: 1}) is True

    def test_b2_typo_and_whitespace_key_variants_rejected(self) -> None:
        """B2: exact-character match required -- typos and whitespace fail.

        Trailing ``s``, trimmed ``t``, leading / trailing space all
        produce keys distinct from the canonical ones. Pins that the
        guard does no fuzzy / prefix / strip matching on key names.
        """
        assert _finding_has_security_scan_metadata({"security_scan_exits": 1}) is False
        assert (
            _finding_has_security_scan_metadata({"security_scan_snippe": "..."})
            is False
        )
        assert _finding_has_security_scan_metadata({" security_scan_exit": 1}) is False
        assert _finding_has_security_scan_metadata({"security_scan_exit ": 1}) is False
        assert (
            _finding_has_security_scan_metadata({"\tsecurity_scan_exit": 1}) is False
        )

    def test_b3_both_keys_present_with_falsy_values(self) -> None:
        """B3: OR with BOTH keys present and BOTH values falsy still True.

        fo112 D2 covers single-key falsy-value semantics. This axis
        pins the dual-presence case: a dict with BOTH scan keys, BOTH
        carrying falsy values (``0`` and ``""``), still returns
        ``True`` because the OR short-circuits on key membership, not
        value truthiness.
        """
        meta = {_EXIT_KEY: 0, _SNIPPET_KEY: ""}
        assert _finding_has_security_scan_metadata(meta) is True

        # And with one None value too.
        meta_none = {_EXIT_KEY: None, _SNIPPET_KEY: None}
        assert _finding_has_security_scan_metadata(meta_none) is True

    def test_b4_key_as_value_rejection_key_divergence(self) -> None:
        """B4: KEY DIVERGENCE -- ``in dict`` checks KEYS, not VALUES.

        A dict where the literal string ``"security_scan_exit"`` appears
        as a VALUE rather than a KEY must NOT match. A refactor to
        ``"security_scan_exit" in meta.values()`` would silently invert
        the contract.
        """
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
        """B5: extra keys do not affect the result -- no whitelist.

        A dict containing the scan key plus arbitrary noise keys still
        returns ``True``. Pins that the guard does NOT validate the
        full key shape -- callers can add any number of unrelated keys.
        """
        meta = {
            _EXIT_KEY: 0,
            "noise_a": [1, 2, 3],
            "noise_b": object(),
            "_internal": None,
            "complex_object": {"nested": True},
        }
        assert _finding_has_security_scan_metadata(meta) is True


# ===========================================================================
# Part C -- security_scan_on_verify_timeline_summary ordering / filtering
# ===========================================================================


class TestPartCSummaryOrderingFiltering:
    """Loop behavior, event-type filter, ordering, and no-category-gate."""

    def test_c1_empty_input_returns_none(self) -> None:
        """C1: empty input list short-circuits to ``None``.

        fo112 D3 uses a non-empty list with the wrong event type;
        this axis pins the never-enter-loop-body case. ``out`` is
        initialised to ``None`` and returned unchanged.
        """
        assert security_scan_on_verify_timeline_summary([]) is None

    def test_c2_list_order_ordering_not_timestamp_key_divergence(self) -> None:
        """C2: KEY DIVERGENCE -- LAST event in the LIST wins, not by ``occurred_at``.

        The loop iterates ``events`` in list order without ``break``;
        each match REPLACES ``out``. So the LAST matching event in
        list order wins, even if its ``occurred_at`` is earlier than
        an earlier-in-list event. A refactor to sort by
        ``occurred_at`` would change semantics for any caller passing
        un-sorted events.
        """
        events = [
            _finding_event(
                event_id="ev-LATER-OCCURRED",
                occurred_at="2099-01-01T00:00:00Z",
                metadata={_EXIT_KEY: 0, _SNIPPET_KEY: "first"},
                payload={"finding_id": "f-FIRST"},
            ),
            _finding_event(
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
        """C3: any event_type other than ``finding.created`` is skipped.

        Extends fo112 D3 (which used only ``stage.started``) across
        the full event-type vocabulary callers might emit. Each of
        these event types, even when carrying scan metadata in the
        ``metadata`` field, must be filtered out.
        """
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
                _finding_event(
                    event_type=et,
                    metadata={_EXIT_KEY: 0, _SNIPPET_KEY: "..."},
                    payload={"finding_id": "f-1"},
                )
            ]
            assert (
                security_scan_on_verify_timeline_summary(events) is None
            ), f"event_type={et!r} should be filtered out"

    def test_c4_mixed_pass_through_keeps_out_none(self) -> None:
        """C4: every event passes event-type filter but every guard fails -> ``None``.

        Three ``finding.created`` events with metadata variants that
        all fail the guard (``{}`` empty dict, ``None``, dict with
        unrelated keys). ``out`` is set to ``None`` initially and
        never reassigned because the guard ``continue``s on each.
        Pins that empty / non-scan finding events do NOT incidentally
        produce a summary.
        """
        events = [
            _finding_event(event_id="ev-1", metadata={}, payload={"finding_id": "f-1"}),
            _finding_event(event_id="ev-2", metadata=None, payload={"finding_id": "f-2"}),
            _finding_event(
                event_id="ev-3",
                metadata={"other_key": "x", "another": 42},
                payload={"finding_id": "f-3"},
            ),
        ]
        assert security_scan_on_verify_timeline_summary(events) is None

    def test_c5_no_category_gate_at_summary_layer(self) -> None:
        """C5: this layer does NOT filter on ``payload.category``.

        A ``finding.created`` event with scan metadata but a
        non-security ``category`` (e.g. ``"performance"``,
        ``"style"``) still produces a summary -- the helper is
        agnostic to finding category. Gating happens at the caller's
        layer, not here.
        """
        for category in ["performance", "style", "lint", "unknown"]:
            events = [
                _finding_event(
                    metadata={_EXIT_KEY: 0},
                    payload={
                        "finding_id": "f-1",
                        "category": category,
                        "severity": "low",
                    },
                )
            ]
            result = security_scan_on_verify_timeline_summary(events)
            assert result is not None, (
                f"category={category!r} should NOT prevent summary"
            )
            assert result["category"] == category
            assert result["severity"] == "low"


# ===========================================================================
# Part D -- payload / source / return-type matrix
# ===========================================================================


class TestPartDPayloadSourceReturnType:
    """Payload coercion, source-split guard, top-level attribution, return type."""

    def test_d1_payload_none_coerced_to_empty_dict(self) -> None:
        """D1: ``payload=None`` still produces a summary; payload keys are ``None``.

        Pins that the ``payload = ev.get("payload"); pl = payload if
        isinstance(payload, dict) else {}`` coercion turns ``None`` into
        ``{}``. All four payload-derived keys (``finding_id``,
        ``category``, ``severity``, ``source_artifact``) come out as
        ``None`` via ``pl.get(...)``. Metadata-derived keys and
        top-level keys are populated normally.
        """
        events = [
            _finding_event(
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
        """D2: non-dict ``payload`` (string, list) coerces to ``pl == {}``.

        A string or list payload is defensively coerced via the
        ``isinstance(payload, dict) else {}`` arm. No
        ``AttributeError`` / ``KeyError`` -- all four payload-derived
        keys are ``None``.
        """
        for bad_payload in ["not-a-dict", [1, 2, 3], 42, True]:
            events = [
                _finding_event(
                    metadata={_EXIT_KEY: 0},
                    payload=bad_payload,
                )
            ]
            result = security_scan_on_verify_timeline_summary(events)
            assert result is not None, (
                f"payload={bad_payload!r} should still produce summary"
            )
            assert result["finding_id"] is None
            assert result["category"] is None
            assert result["severity"] is None
            assert result["source_artifact"] is None
            # Metadata-derived keys still populated.
            assert result["security_scan_exit"] == 0

    def test_d3_source_split_guard_metadata_only_key_divergence(self) -> None:
        """D3: KEY DIVERGENCE -- guard checks ``meta`` only, NOT ``payload``.

        If scan keys live in ``payload`` but ``metadata`` is empty
        (or missing entirely), the guard fails and the loop
        ``continue``s. Summary stays ``None``. Pins that the helper
        does NOT fall back to ``payload`` for the guard -- a refactor
        that did so would silently surface findings whose data was
        misrouted.
        """
        # Scan keys in payload only; metadata empty.
        events_payload_only = [
            _finding_event(
                metadata={},
                payload={
                    _EXIT_KEY: 1,
                    _SNIPPET_KEY: "scan-data-misrouted",
                    "finding_id": "f-1",
                },
            )
        ]
        assert (
            security_scan_on_verify_timeline_summary(events_payload_only) is None
        )

        # Same with metadata explicitly None.
        events_meta_none = [
            _finding_event(
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
        assert (
            security_scan_on_verify_timeline_summary(events_meta_missing) is None
        )

    def test_d4_top_level_event_id_and_occurred_at_attribution(self) -> None:
        """D4: top-level ``event_id`` / ``occurred_at`` win over payload keys.

        Even if ``payload`` happens to carry the same key names
        (``event_id``, ``occurred_at``), the summary takes them from
        the top-level event dict via ``ev.get(...)``, NOT from
        ``pl.get(...)``. Pins the source-field-attribution contract.
        """
        events = [
            _finding_event(
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
        """D5: KEY DIVERGENCE -- return type is plain ``dict``, mutable, JSON-safe.

        Pins that the helper returns a builtin ``dict`` instance --
        NOT a ``TypedDict`` (which has no runtime class anyway),
        NOT a frozen dataclass, NOT an ``OrderedDict`` (despite the
        literal order). The dict is mutable (callers may add keys)
        and ``json.dumps``-serializable (all values are primitive).
        Also pins the exact 10-key shape.
        """
        events = [
            _finding_event(
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
