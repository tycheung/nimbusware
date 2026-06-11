from __future__ import annotations

from typing import Any
from uuid import UUID

from nimbusware_api.routes.runs import (
    _finding_has_security_scan_metadata,
    agent_evaluator_timeline_summary,
    integrator_gate_timeline_summary,
    run_escalated_timeline_summary,
    security_scan_on_verify_timeline_summary,
    self_refinement_timeline_summary,
)

_EVENT_TYPE_GATE = "gate.decision.emitted"
_EVENT_TYPE_STAGE = "stage.started"
_EVENT_TYPE_ESCALATED = "run.escalated"
_EVENT_TYPE_FINDING = "finding.created"
_EVENT_TYPE_RUN_CREATED = "run.created"

_RID1 = UUID("11111111-1111-4111-8111-111111111111")
_RID2 = UUID("22222222-2222-4222-8222-222222222222")
_RID3 = UUID("33333333-3333-4333-8333-333333333333")
_RID4 = UUID("44444444-4444-4444-8444-444444444444")
_ISO_NOW = "2026-05-12T12:34:56+00:00"
_ISO_LATER = "2026-05-12T12:35:00+00:00"


def _gate_decision_event(
    *,
    event_id: UUID,
    metadata: Any,
    payload: Any,
    event_type: str = _EVENT_TYPE_GATE,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    """Construct a minimal dict-shaped ``gate.decision.emitted`` event.

    Note ``metadata`` / ``payload`` accept ``Any`` so axes can pass
    non-dict / ``None`` values and force the defensive arms in
    ``integrator_gate_timeline_summary``.
    """
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


def _stage_started_event(
    *,
    event_id: UUID,
    payload: Any,
    metadata: Any = None,
    event_type: str = _EVENT_TYPE_STAGE,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    """Construct a minimal dict-shaped ``stage.started`` event."""
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


def _run_escalated_event(
    *,
    event_id: UUID,
    payload: Any,
    event_type: str = _EVENT_TYPE_ESCALATED,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    """Construct a minimal dict-shaped ``run.escalated`` event."""
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "payload": payload,
    }


def _finding_created_event(
    *,
    event_id: UUID,
    metadata: Any,
    payload: Any,
    event_type: str = _EVENT_TYPE_FINDING,
    occurred_at: str = _ISO_NOW,
) -> dict[str, Any]:
    """Construct a minimal dict-shaped ``finding.created`` event."""
    return {
        "event_type": event_type,
        "event_id": str(event_id),
        "occurred_at": occurred_at,
        "metadata": metadata,
        "payload": payload,
    }


def test_integrator_gate_timeline_summary_direct_contract_5_axis() -> None:
    assert integrator_gate_timeline_summary([]) is None, (
        "A1: empty event list must return ``None`` (the function pre-allocates "
        "``out = None`` then never overwrites). A refactor that pre-allocated "
        "an empty dict ``{}`` and returned it would break consumers that "
        "use ``if integrator_gate is not None:`` as the populated-check."
    )

    non_matching_events = [
        _stage_started_event(
            event_id=_RID1,
            payload={"stage_name": "plan:initial"},
        ),
        {"event_type": _EVENT_TYPE_RUN_CREATED, "event_id": str(_RID2)},
        _finding_created_event(event_id=_RID3, metadata={}, payload={}),
        _run_escalated_event(event_id=_RID4, payload={}),
    ]
    assert integrator_gate_timeline_summary(non_matching_events) is None, (
        "A2: a list of events whose ``event_type`` is never "
        "``gate.decision.emitted`` must return ``None``. The event_type "
        "filter MUST precede metadata inspection -- a refactor that "
        "inverted the order would crash on the ``RUN_CREATED`` event "
        "(no metadata key) or emit summaries for the wrong types."
    )

    metadata_skip_variants: list[tuple[str, Any]] = [
        ("none", None),
        ("empty_dict", {}),
        ("integrator_gate_false", {"integrator_gate": False}),
        ("integrator_gate_truthy_int", {"integrator_gate": 1}),
        ("integrator_gate_str_True", {"integrator_gate": "True"}),
        ("integrator_gate_none", {"integrator_gate": None}),
        ("non_dict_str", "not-a-dict"),
        ("non_dict_list", ["integrator_gate", True]),
    ]
    for name, meta_variant in metadata_skip_variants:
        events = [
            _gate_decision_event(
                event_id=_RID1,
                metadata=meta_variant,
                payload={"stage_name": "bundle_compatibility", "verdict": "PASS"},
            ),
        ]
        got = integrator_gate_timeline_summary(events)
        assert got is None, (
            f"A3 case={name!r} meta={meta_variant!r}: compound guard must "
            f"skip event when metadata is non-dict OR missing/non-identical-True "
            f"``integrator_gate``. A refactor to ``not meta.get(...)`` would "
            f"accept the truthy-int / str-True variants; a refactor that "
            f"dropped the ``isinstance(meta, dict)`` half would crash on "
            f"the non-dict variants. Got: {got!r}"
        )

    happy_meta = {
        "integrator_gate": True,
        "bundle_id": "auth-rbac-starter",
        "bundle_title": "Admin RBAC starter",
        "integrator_score": 0.9,
        "min_score_to_pass": 0.3,
        "integrator_project_tags": ["auth-rbac-starter"],
        "integrator_bundle_tags": ["auth", "rbac"],
        "integrator_matched_tags": ["auth"],
    }
    happy_payload = {
        "stage_name": "bundle_compatibility",
        "verdict": "PASS",
        "failure_reason_code": None,
    }
    happy_events = [
        _gate_decision_event(
            event_id=_RID1,
            metadata=happy_meta,
            payload=happy_payload,
            occurred_at=_ISO_NOW,
        ),
    ]
    got = integrator_gate_timeline_summary(happy_events)
    assert got is not None
    expected_keys = {
        "event_id",
        "occurred_at",
        "stage_name",
        "verdict",
        "failure_reason_code",
        "bundle_id",
        "bundle_title",
        "integrator_score",
        "min_score_to_pass",
        "integrator_project_tags",
        "integrator_bundle_tags",
        "integrator_matched_tags",
    }
    assert set(got.keys()) == expected_keys, (
        f"A4: emitted summary must have exactly 12 keys (no extras, none "
        f"missing). A refactor that added a 13th key would still pass the "
        f"happy ``test_api.py`` test but break this axis. Got "
        f"keys={set(got.keys())!r}"
    )
    assert got["event_id"] == str(_RID1)
    assert got["occurred_at"] == _ISO_NOW
    assert got["stage_name"] == "bundle_compatibility"
    assert got["verdict"] == "PASS"
    assert got["failure_reason_code"] is None
    assert got["bundle_id"] == "auth-rbac-starter"
    assert got["bundle_title"] == "Admin RBAC starter"
    assert got["integrator_score"] == 0.9
    assert got["min_score_to_pass"] == 0.3
    assert got["integrator_project_tags"] == ["auth-rbac-starter"]
    assert got["integrator_bundle_tags"] == ["auth", "rbac"]
    assert got["integrator_matched_tags"] == ["auth"]

    second_meta = dict(happy_meta)
    second_meta["bundle_id"] = "search-fts-starter"
    second_meta["integrator_score"] = 0.42
    latest_wins_events = [
        _gate_decision_event(
            event_id=_RID1,
            metadata=happy_meta,
            payload=happy_payload,
            occurred_at=_ISO_NOW,
        ),
        _stage_started_event(event_id=_RID3, payload={"stage_name": "verify"}),
        _gate_decision_event(
            event_id=_RID2,
            metadata=second_meta,
            payload={
                "stage_name": "bundle_compatibility",
                "verdict": "FAIL",
                "failure_reason_code": "score_below_min",
            },
            occurred_at=_ISO_LATER,
        ),
    ]
    got_latest = integrator_gate_timeline_summary(latest_wins_events)
    assert got_latest is not None
    assert got_latest["event_id"] == str(_RID2), (
        "A5: latest-wins -- the SECOND matching event's ``event_id`` must "
        "win. The interleaved ``stage.started`` event must not affect the "
        "loop. A refactor that ``break``ed on the first match would emit "
        "the first event's id."
    )
    assert got_latest["bundle_id"] == "search-fts-starter"
    assert got_latest["integrator_score"] == 0.42
    assert got_latest["verdict"] == "FAIL"
    assert got_latest["failure_reason_code"] == "score_below_min"


def test_agent_evaluator_timeline_summary_persona_split_5_axis() -> None:
    wrong_type_events = [
        _gate_decision_event(
            event_id=_RID1,
            metadata={"integrator_gate": True, "bundle_id": "x"},
            payload={"stage_name": "agent_eval:default", "verdict": "PASS"},
        ),
        _finding_created_event(
            event_id=_RID2,
            metadata={"security_scan_exit": 0},
            payload={"stage_name": "agent_eval:default"},
        ),
    ]
    assert agent_evaluator_timeline_summary(wrong_type_events) is None, (
        "B1: event_type filter MUST precede payload inspection -- even when "
        "the payload's ``stage_name`` starts with ``agent_eval:`` the event "
        "is skipped unless its ``event_type`` is ``stage.started``."
    )

    prefix_skip_variants: list[tuple[str, Any]] = [
        ("different_prefix", {"stage_name": "plan:initial", "attempt": 1}),
        ("no_trailing_colon", {"stage_name": "agent_eval", "attempt": 1}),
        ("only_partial_prefix", {"stage_name": "agent_eva:default", "attempt": 1}),
        ("stage_name_non_string_int", {"stage_name": 42, "attempt": 1}),
        ("stage_name_none", {"stage_name": None, "attempt": 1}),
        ("non_dict_payload_str", "oops"),
        ("non_dict_payload_none", None),
        ("non_dict_payload_list", ["agent_eval:default"]),
    ]
    for name, payload_variant in prefix_skip_variants:
        events = [_stage_started_event(event_id=_RID1, payload=payload_variant)]
        assert agent_evaluator_timeline_summary(events) is None, (
            f"B2 case={name!r} payload={payload_variant!r}: compound "
            f"``isinstance(sn, str) AND sn.startswith('agent_eval:')`` gate "
            f"must skip. The no_trailing_colon case pins that the prefix "
            f"includes the ``:`` (a refactor to ``agent_eval`` without "
            f"colon would silently match ``agent_evaluator:foo``). The "
            f"non-dict payload cases pin the ``pl = {{}} if not isinstance"
            f"(payload, dict) else payload`` coercion -> "
            f"``pl.get('stage_name')`` is then ``None``."
        )

    persona_cases: list[tuple[str, str, str]] = [
        ("simple_lowercase", "agent_eval:default", "default"),
        ("multiword_with_underscore", "agent_eval:backend_engineer", "backend_engineer"),
        ("multi_segment_colons", "agent_eval:foo:bar:baz", "foo:bar:baz"),
        ("single_char", "agent_eval:a", "a"),
        ("uppercase_and_digits", "agent_eval:Ops7", "Ops7"),
    ]
    for name, stage_name, expected_persona in persona_cases:
        events = [
            _stage_started_event(event_id=_RID1, payload={"stage_name": stage_name, "attempt": 3}),
        ]
        got = agent_evaluator_timeline_summary(events)
        assert got is not None, f"B3 case={name!r}: expected emission"
        assert got["stage_name"] == stage_name, (
            f"B3 case={name!r}: emitted stage_name must equal full input "
            f"({stage_name!r}); got {got['stage_name']!r}"
        )
        assert got["persona_id"] == expected_persona, (
            f"B3 case={name!r}: persona_id must equal the suffix after "
            f"``agent_eval:`` ({expected_persona!r}); the multi-segment "
            f"case pins that the suffix is preserved verbatim (NOT split "
            f"again on a later colon). Got persona_id={got['persona_id']!r}"
        )
        assert got["attempt"] == 3

    empty_suffix_events = [
        _stage_started_event(event_id=_RID2, payload={"stage_name": "agent_eval:", "attempt": 0}),
    ]
    got_empty = agent_evaluator_timeline_summary(empty_suffix_events)
    assert got_empty is not None, (
        "B4: ``agent_eval:`` (just the prefix) DOES start with the prefix, "
        "so the event MUST be emitted (NOT skipped); a refactor that "
        "skipped on empty suffix would lose attempt-zero diagnostic events"
    )
    assert got_empty["stage_name"] == "agent_eval:"
    assert got_empty["persona_id"] is None, (
        f"B4 KEY DIVERGENCE: empty suffix MUST collapse to ``None`` via "
        f"``suffix if suffix else None``; a refactor that returned "
        f"``suffix`` directly would emit ``persona_id=''`` (empty string) "
        f"and break downstream JSON consumers that destructure persona_id "
        f"as ``str | None``. Got persona_id={got_empty['persona_id']!r}"
    )
    assert got_empty["attempt"] == 0

    latest_wins_events = [
        _stage_started_event(event_id=_RID1, payload={"stage_name": "agent_eval:a", "attempt": 1}),
        _stage_started_event(event_id=_RID2, payload="non-dict-payload-oops"),
        _stage_started_event(event_id=_RID3, payload={"stage_name": "agent_eval:c", "attempt": 2}),
    ]
    got_latest = agent_evaluator_timeline_summary(latest_wins_events)
    assert got_latest is not None
    assert got_latest["event_id"] == str(_RID3), (
        "B5: latest-wins -- the third event's id must win. The middle "
        "event's non-dict payload is coerced to ``{}`` and then filtered "
        "out by the stage_name gate (since ``pl.get('stage_name') is "
        "None``), so it must NOT overwrite the first match nor block the "
        "third match. Pins the payload-coercion-then-filter ordering."
    )
    assert got_latest["persona_id"] == "c"
    assert got_latest["stage_name"] == "agent_eval:c"


def test_self_refinement_and_run_escalated_summary_5_axis() -> None:
    sr_metadata = {"self_refinement": {"version": "v2", "description": "second pass"}}
    sr_payload = {"stage_name": "self_refinement:policy", "attempt": 2}
    events_happy = [
        _stage_started_event(
            event_id=_RID1, payload=sr_payload, metadata=sr_metadata, occurred_at=_ISO_NOW
        ),
    ]
    got_sr = self_refinement_timeline_summary(events_happy)
    assert got_sr is not None
    assert set(got_sr.keys()) == {
        "event_id",
        "occurred_at",
        "stage_name",
        "attempt",
        "version",
        "description",
        "marker_count",
        "first_marker_occurred_at",
        "last_marker_occurred_at",
    }, f"C1: emitted summary must have exactly 9 keys; got {set(got_sr.keys())!r}"
    assert got_sr["event_id"] == str(_RID1)
    assert got_sr["occurred_at"] == _ISO_NOW
    assert got_sr["stage_name"] == "self_refinement:policy"
    assert got_sr["attempt"] == 2
    assert got_sr["version"] == "v2"
    assert got_sr["description"] == "second pass"
    assert got_sr["marker_count"] == 1
    assert got_sr["first_marker_occurred_at"] == _ISO_NOW
    assert got_sr["last_marker_occurred_at"] == _ISO_NOW

    exact_match_skip_variants: list[tuple[str, str]] = [
        ("different_suffix", "self_refinement:other"),
        ("no_colon", "self_refinement"),
        ("trailing_extra_segment", "self_refinement:policy:extra"),
        ("policy_prefix_only", "self_refinement:polic"),
        ("with_trailing_colon", "self_refinement:policy:"),
    ]
    for name, sn in exact_match_skip_variants:
        events = [
            _stage_started_event(
                event_id=_RID1,
                payload={"stage_name": sn, "attempt": 1},
                metadata=sr_metadata,
            ),
        ]
        got = self_refinement_timeline_summary(events)
        assert got is None, (
            f"C2 case={name!r} stage_name={sn!r}: self_refinement uses "
            f"EXACT equality (``sn != 'self_refinement:policy'`` -> "
            f"continue), NOT ``startswith``. A refactor to prefix matching "
            f"(mirroring agent_evaluator) would silently emit summaries "
            f"for unrelated ``self_refinement:*`` stages. Got: {got!r}"
        )

    degraded_meta_variants: list[tuple[str, Any]] = [
        ("metadata_none", None),
        ("metadata_empty", {}),
        ("metadata_self_refinement_none", {"self_refinement": None}),
        ("metadata_self_refinement_non_dict", {"self_refinement": "not-a-dict"}),
        ("metadata_self_refinement_list", {"self_refinement": ["v1"]}),
        ("metadata_non_dict_str", "garbage"),
    ]
    for name, meta_variant in degraded_meta_variants:
        events = [
            _stage_started_event(
                event_id=_RID2,
                payload={"stage_name": "self_refinement:policy", "attempt": 7},
                metadata=meta_variant,
            ),
        ]
        got = self_refinement_timeline_summary(events)
        assert got is not None, (
            f"C3 case={name!r} meta={meta_variant!r}: KEY DIVERGENCE from "
            f"integrator_gate -- self_refinement EMITS a summary with "
            f"``version=None``, ``description=None`` even when metadata "
            f"is degraded. integrator_gate would SKIP entirely. A refactor "
            f"that unified the two would silently flip the emission policy. "
            f"Got: None"
        )
        assert got["event_id"] == str(_RID2)
        assert got["stage_name"] == "self_refinement:policy"
        assert got["attempt"] == 7, (
            f"C3 case={name!r}: ``attempt`` must come from payload (NOT "
            f"metadata) and survive degraded metadata; got {got['attempt']!r}"
        )
        assert got["version"] is None, (
            f"C3 case={name!r}: ``version`` must default to None when "
            f"nested ``self_refinement`` dict is missing or non-dict; got "
            f"{got['version']!r}"
        )
        assert got["description"] is None, (
            f"C3 case={name!r}: ``description`` must default to None when "
            f"nested ``self_refinement`` dict is missing or non-dict; got "
            f"{got['description']!r}"
        )
        assert got["marker_count"] == 1, (
            f"C3 case={name!r}: single matching marker in session; got {got['marker_count']!r}"
        )
        assert got["first_marker_occurred_at"] == got["occurred_at"], (
            f"C3 case={name!r}: first marker timestamp must match sole event"
        )
        assert got["last_marker_occurred_at"] == got["occurred_at"], (
            f"C3 case={name!r}: last marker timestamp must match sole event"
        )

    events_two_sr = [
        _stage_started_event(
            event_id=_RID1,
            payload=sr_payload,
            metadata=sr_metadata,
            occurred_at=_ISO_NOW,
        ),
        _stage_started_event(
            event_id=_RID2,
            payload=sr_payload,
            metadata={"self_refinement": {"version": "v3", "description": "last row"}},
            occurred_at=_ISO_LATER,
        ),
    ]
    got_two = self_refinement_timeline_summary(events_two_sr)
    assert got_two is not None
    assert got_two["marker_count"] == 2
    assert got_two["first_marker_occurred_at"] == _ISO_NOW
    assert got_two["last_marker_occurred_at"] == _ISO_LATER
    assert got_two["occurred_at"] == _ISO_LATER

    esc_payload = {
        "actor_id": "human:ops",
        "reason_code": "cumulative_stage_failures",
        "policy_snapshot_id": "snap-1",
        "notes": "literal note from operator",
    }
    esc_events = [
        _run_escalated_event(event_id=_RID3, payload=esc_payload, occurred_at=_ISO_LATER),
    ]
    got_esc = run_escalated_timeline_summary(esc_events)
    assert got_esc is not None
    assert set(got_esc.keys()) == {
        "event_id",
        "occurred_at",
        "actor_id",
        "reason_code",
        "policy_snapshot_id",
        "notes",
    }, (
        f"C4: emitted summary must have exactly 6 keys (payload-only -- "
        f"no metadata extraction); got {set(got_esc.keys())!r}"
    )
    assert got_esc["event_id"] == str(_RID3)
    assert got_esc["occurred_at"] == _ISO_LATER
    assert got_esc["actor_id"] == "human:ops"
    assert got_esc["reason_code"] == "cumulative_stage_failures"
    assert got_esc["policy_snapshot_id"] == "snap-1"
    assert got_esc["notes"] == "literal note from operator"

    bad_payload_variants: list[tuple[str, Any]] = [
        ("payload_none", None),
        ("payload_str", "garbage"),
        ("payload_list", ["actor", "reason"]),
        ("payload_int", 42),
    ]
    for name, payload_variant in bad_payload_variants:
        events = [_run_escalated_event(event_id=_RID4, payload=payload_variant)]
        got = run_escalated_timeline_summary(events)
        assert got is not None, (
            f"C5 case={name!r}: KEY DIVERGENCE from integrator_gate -- "
            f"run_escalated has NO metadata guard and emits ANY event "
            f"with the right event_type, even on bad payload. Got: None"
        )
        assert got["event_id"] == str(_RID4)
        assert got["actor_id"] is None, (
            f"C5 case={name!r}: ``actor_id`` defaults to None via the "
            f"``pl = {{}} if not isinstance(payload, dict) else payload`` "
            f"coercion at runs.py:146; got {got['actor_id']!r}"
        )
        assert got["reason_code"] is None
        assert got["policy_snapshot_id"] is None
        assert got["notes"] is None


def test_security_scan_summary_and_guard_5_axis() -> None:
    non_dict_inputs: list[tuple[str, Any]] = [
        ("none", None),
        ("string", "not-a-dict"),
        ("list", ["security_scan_exit"]),
        ("tuple", ("security_scan_exit", 0)),
        ("int", 42),
        ("zero", 0),
        ("true", True),
        ("false", False),
    ]
    for name, value in non_dict_inputs:
        assert _finding_has_security_scan_metadata(value) is False, (
            f"D1 case={name!r} value={value!r}: non-dict inputs must "
            f"return ``False`` via the ``isinstance(meta, dict)`` early-out. "
            f"A refactor that dropped the guard would crash on ``in`` "
            f"with non-iterable inputs (int, bool); for iterables it "
            f"would silently emit ``True``/``False`` based on membership "
            f"semantics that vary by type (list vs tuple)."
        )

    or_semantics_cases: list[tuple[str, dict[str, Any], bool]] = [
        ("empty_dict", {}, False),
        ("unrelated_keys_only", {"unrelated": "x", "other": 1}, False),
        ("exit_only_zero", {"security_scan_exit": 0}, True),
        ("exit_only_non_zero", {"security_scan_exit": 1}, True),
        ("snippet_only", {"security_scan_snippet": "ok"}, True),
        ("snippet_only_empty_str", {"security_scan_snippet": ""}, True),
        ("both_keys", {"security_scan_exit": 0, "security_scan_snippet": "ok"}, True),
        ("exit_none_value", {"security_scan_exit": None}, True),
        ("snippet_none_value", {"security_scan_snippet": None}, True),
    ]
    for name, meta_variant, expected in or_semantics_cases:
        got = _finding_has_security_scan_metadata(meta_variant)
        assert got is expected, (
            f"D2 case={name!r} meta={meta_variant!r}: KEY DIVERGENCE -- "
            f"membership-OR semantics, NOT value-AND. The exit_only_zero / "
            f"snippet_only_empty_str / exit_none_value cases all pin that "
            f"``key in meta`` is membership (NOT ``meta.get(key)`` "
            f"truthiness). A refactor to truthiness would mark a "
            f"successful zero-exit scan as missing metadata. "
            f"Expected {expected!r}, got {got!r}"
        )

    wrong_type_with_scan_meta = [
        _stage_started_event(
            event_id=_RID1,
            payload={"stage_name": "verify"},
            metadata={
                "security_scan_exit": 0,
                "security_scan_snippet": "fake",
            },
        ),
    ]
    assert security_scan_on_verify_timeline_summary(wrong_type_with_scan_meta) is None, (
        "D3 step-1: event_type filter precedes guard; a ``stage.started`` "
        "event with full scan metadata must return ``None``"
    )

    finding_without_scan_meta = [
        _finding_created_event(
            event_id=_RID2,
            metadata={"category": "lint", "unrelated": True},
            payload={"finding_id": "f-99", "category": "lint", "severity": "low"},
        ),
    ]
    assert security_scan_on_verify_timeline_summary(finding_without_scan_meta) is None, (
        "D3 step-2: ``finding.created`` event without either scan key in "
        "metadata must return ``None`` via the ``_finding_has_security_scan_metadata`` "
        "guard. Pins the two-stage filter (type first, then guard)."
    )

    happy_meta = {
        "security_scan_exit": 1,
        "security_scan_ruff_exit": 1,
        "security_scan_bandit_exit": 0,
        "security_scan_snippet": "CVE-2024-12345 detected in dependency\n",
    }
    happy_payload = {
        "finding_id": "f-1",
        "category": "security",
        "severity": "high",
        "source_artifact": "src/app.py",
    }
    happy_events = [
        _finding_created_event(
            event_id=_RID3,
            metadata=happy_meta,
            payload=happy_payload,
            occurred_at=_ISO_NOW,
        ),
    ]
    got_ss = security_scan_on_verify_timeline_summary(happy_events)
    assert got_ss is not None
    assert set(got_ss.keys()) == {
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
    }, f"D4: emitted summary must have exactly 10 keys; got {set(got_ss.keys())!r}"
    assert got_ss["event_id"] == str(_RID3)
    assert got_ss["occurred_at"] == _ISO_NOW
    assert got_ss["finding_id"] == "f-1"
    assert got_ss["category"] == "security"
    assert got_ss["severity"] == "high"
    assert got_ss["source_artifact"] == "src/app.py"
    assert got_ss["security_scan_exit"] == 1
    assert got_ss["security_scan_ruff_exit"] == 1
    assert got_ss["security_scan_bandit_exit"] == 0
    assert got_ss["security_scan_snippet"] == "CVE-2024-12345 detected in dependency\n"

    second_meta = {
        "security_scan_exit": 0,
        "security_scan_ruff_exit": 0,
        "security_scan_bandit_exit": 0,
        "security_scan_snippet": "clean",
    }
    second_payload = {
        "finding_id": "f-2",
        "category": "security",
        "severity": "info",
        "source_artifact": "src/db.py",
    }
    latest_wins_events = [
        _finding_created_event(
            event_id=_RID1,
            metadata=happy_meta,
            payload=happy_payload,
            occurred_at=_ISO_NOW,
        ),
        _finding_created_event(
            event_id=_RID3,
            metadata={"category": "lint", "unrelated": True},
            payload={"finding_id": "f-99", "category": "lint"},
            occurred_at=_ISO_LATER,
        ),
        _finding_created_event(
            event_id=_RID2,
            metadata=second_meta,
            payload=second_payload,
            occurred_at=_ISO_LATER,
        ),
    ]
    got_latest = security_scan_on_verify_timeline_summary(latest_wins_events)
    assert got_latest is not None
    assert got_latest["event_id"] == str(_RID2), (
        "D5: latest-wins -- the LAST scan-bearing finding must win. The "
        "interleaved finding WITHOUT scan keys must be silently skipped "
        "(NOT overwrite the first match with null fields)."
    )
    assert got_latest["finding_id"] == "f-2"
    assert got_latest["security_scan_exit"] == 0
    assert got_latest["security_scan_ruff_exit"] == 0
    assert got_latest["security_scan_bandit_exit"] == 0
    assert got_latest["security_scan_snippet"] == "clean"
    assert got_latest["source_artifact"] == "src/db.py"
