from __future__ import annotations

from typing import Any

from api.routes.runs import (
    _finding_has_security_scan_metadata,
    agent_evaluator_timeline_summary,
    integrator_gate_timeline_summary,
    run_escalated_timeline_summary,
    security_scan_on_verify_timeline_summary,
    self_refinement_timeline_summary,
)
from unit.composite_contract_fixtures import (
    _ISO_LATER,
    _ISO_NOW,
    EVENT_TYPE_RUN_CREATED,
    RID1,
    RID2,
    RID3,
    RID4,
    finding_created_event,
    gate_decision_event,
    run_escalated_event,
    stage_started_event,
)

INTEGRATOR_GATE_EXPECTED_KEYS = frozenset(
    {
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
    },
)

HAPPY_INTEGRATOR_META = {
    "integrator_gate": True,
    "bundle_id": "auth-rbac-starter",
    "bundle_title": "Admin RBAC starter",
    "integrator_score": 0.9,
    "min_score_to_pass": 0.3,
    "integrator_project_tags": ["auth-rbac-starter"],
    "integrator_bundle_tags": ["auth", "rbac"],
    "integrator_matched_tags": ["auth"],
}

HAPPY_INTEGRATOR_PAYLOAD = {
    "stage_name": "bundle_compatibility",
    "verdict": "PASS",
    "failure_reason_code": None,
}

SR_METADATA = {"self_refinement": {"version": "v2", "description": "second pass"}}
SR_PAYLOAD = {"stage_name": "self_refinement:policy", "attempt": 2}

SELF_REFINEMENT_EXPECTED_KEYS = frozenset(
    {
        "event_id",
        "occurred_at",
        "stage_name",
        "attempt",
        "version",
        "description",
        "marker_count",
        "first_marker_occurred_at",
        "last_marker_occurred_at",
    },
)

RUN_ESCALATED_EXPECTED_KEYS = frozenset(
    {
        "event_id",
        "occurred_at",
        "actor_id",
        "reason_code",
        "policy_snapshot_id",
        "notes",
    },
)

SECURITY_SCAN_EXPECTED_KEYS = frozenset(
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

HAPPY_SCAN_META = {
    "security_scan_exit": 1,
    "security_scan_ruff_exit": 1,
    "security_scan_bandit_exit": 0,
    "security_scan_snippet": "CVE-2024-12345 detected in dependency\n",
}

HAPPY_SCAN_PAYLOAD = {
    "finding_id": "f-1",
    "category": "security",
    "severity": "high",
    "source_artifact": "src/app.py",
}


def _validate_integrator_a1(case: dict[str, Any], actual: Any) -> None:
    assert actual is None, (
        "A1: empty event list must return ``None`` (the function pre-allocates "
        "``out = None`` then never overwrites). A refactor that pre-allocated "
        "an empty dict ``{}`` and returned it would break consumers that "
        "use ``if integrator_gate is not None:`` as the populated-check."
    )


def _validate_integrator_a2(case: dict[str, Any], actual: Any) -> None:
    assert actual is None, (
        "A2: a list of events whose ``event_type`` is never "
        "``gate.decision.emitted`` must return ``None``. The event_type "
        "filter MUST precede metadata inspection -- a refactor that "
        "inverted the order would crash on the ``RUN_CREATED`` event "
        "(no metadata key) or emit summaries for the wrong types."
    )


def _validate_integrator_a3(case: dict[str, Any], actual: Any) -> None:
    name = case["name"]
    meta_variant = case["meta_variant"]
    assert actual is None, (
        f"A3 case={name!r} meta={meta_variant!r}: compound guard must "
        f"skip event when metadata is non-dict OR missing/non-identical-True "
        f"``integrator_gate``. A refactor to ``not meta.get(...)`` would "
        f"accept the truthy-int / str-True variants; a refactor that "
        f"dropped the ``isinstance(meta, dict)`` half would crash on "
        f"the non-dict variants. Got: {actual!r}"
    )


def _validate_integrator_a4(case: dict[str, Any], actual: Any) -> None:
    assert actual is not None
    assert set(actual.keys()) == INTEGRATOR_GATE_EXPECTED_KEYS, (
        f"A4: emitted summary must have exactly 12 keys (no extras, none "
        f"missing). A refactor that added a 13th key would still pass the "
        f"happy ``test_api.py`` test but break this axis. Got "
        f"keys={set(actual.keys())!r}"
    )
    assert actual["event_id"] == str(RID1)
    assert actual["occurred_at"] == _ISO_NOW
    assert actual["stage_name"] == "bundle_compatibility"
    assert actual["verdict"] == "PASS"
    assert actual["failure_reason_code"] is None
    assert actual["bundle_id"] == "auth-rbac-starter"
    assert actual["bundle_title"] == "Admin RBAC starter"
    assert actual["integrator_score"] == 0.9
    assert actual["min_score_to_pass"] == 0.3
    assert actual["integrator_project_tags"] == ["auth-rbac-starter"]
    assert actual["integrator_bundle_tags"] == ["auth", "rbac"]
    assert actual["integrator_matched_tags"] == ["auth"]


def _validate_integrator_a5(case: dict[str, Any], actual: Any) -> None:
    assert actual is not None
    assert actual["event_id"] == str(RID2), (
        "A5: latest-wins -- the SECOND matching event's ``event_id`` must "
        "win. The interleaved ``stage.started`` event must not affect the "
        "loop. A refactor that ``break``ed on the first match would emit "
        "the first event's id."
    )
    assert actual["bundle_id"] == "search-fts-starter"
    assert actual["integrator_score"] == 0.42
    assert actual["verdict"] == "FAIL"
    assert actual["failure_reason_code"] == "score_below_min"


def _validate_agent_b1(case: dict[str, Any], actual: Any) -> None:
    assert actual is None, (
        "B1: event_type filter MUST precede payload inspection -- even when "
        "the payload's ``stage_name`` starts with ``agent_eval:`` the event "
        "is skipped unless its ``event_type`` is ``stage.started``."
    )


def _validate_agent_b2(case: dict[str, Any], actual: Any) -> None:
    name = case["name"]
    payload_variant = case["payload_variant"]
    assert actual is None, (
        f"B2 case={name!r} payload={payload_variant!r}: compound "
        f"``isinstance(sn, str) AND sn.startswith('agent_eval:')`` gate "
        f"must skip. The no_trailing_colon case pins that the prefix "
        f"includes the ``:`` (a refactor to ``agent_eval`` without "
        f"colon would silently match ``agent_evaluator:foo``). The "
        f"non-dict payload cases pin the ``pl = {{}} if not isinstance"
        f"(payload, dict) else payload`` coercion -> "
        f"``pl.get('stage_name')`` is then ``None``."
    )


def _validate_agent_b3(case: dict[str, Any], actual: Any) -> None:
    name = case["name"]
    stage_name = case["stage_name"]
    expected_persona = case["expected_persona"]
    assert actual is not None, f"B3 case={name!r}: expected emission"
    assert actual["stage_name"] == stage_name, (
        f"B3 case={name!r}: emitted stage_name must equal full input "
        f"({stage_name!r}); got {actual['stage_name']!r}"
    )
    assert actual["persona_id"] == expected_persona, (
        f"B3 case={name!r}: persona_id must equal the suffix after "
        f"``agent_eval:`` ({expected_persona!r}); the multi-segment "
        f"case pins that the suffix is preserved verbatim (NOT split "
        f"again on a later colon). Got persona_id={actual['persona_id']!r}"
    )
    assert actual["attempt"] == 3


def _validate_agent_b4(case: dict[str, Any], actual: Any) -> None:
    assert actual is not None, (
        "B4: ``agent_eval:`` (just the prefix) DOES start with the prefix, "
        "so the event MUST be emitted (NOT skipped); a refactor that "
        "skipped on empty suffix would lose attempt-zero diagnostic events"
    )
    assert actual["stage_name"] == "agent_eval:"
    assert actual["persona_id"] is None, (
        f"B4 KEY DIVERGENCE: empty suffix MUST collapse to ``None`` via "
        f"``suffix if suffix else None``; a refactor that returned "
        f"``suffix`` directly would emit ``persona_id=''`` (empty string) "
        f"and break downstream JSON consumers that destructure persona_id "
        f"as ``str | None``. Got persona_id={actual['persona_id']!r}"
    )
    assert actual["attempt"] == 0


def _validate_agent_b5(case: dict[str, Any], actual: Any) -> None:
    assert actual is not None
    assert actual["event_id"] == str(RID3), (
        "B5: latest-wins -- the third event's id must win. The middle "
        "event's non-dict payload is coerced to ``{}`` and then filtered "
        "out by the stage_name gate (since ``pl.get('stage_name') is "
        "None``), so it must NOT overwrite the first match nor block the "
        "third match. Pins the payload-coercion-then-filter ordering."
    )
    assert actual["persona_id"] == "c"
    assert actual["stage_name"] == "agent_eval:c"


def _validate_self_refinement_c1(case: dict[str, Any], actual: Any) -> None:
    assert actual is not None
    assert set(actual.keys()) == SELF_REFINEMENT_EXPECTED_KEYS, (
        f"C1: emitted summary must have exactly 9 keys; got {set(actual.keys())!r}"
    )
    assert actual["event_id"] == str(RID1)
    assert actual["occurred_at"] == _ISO_NOW
    assert actual["stage_name"] == "self_refinement:policy"
    assert actual["attempt"] == 2
    assert actual["version"] == "v2"
    assert actual["description"] == "second pass"
    assert actual["marker_count"] == 1
    assert actual["first_marker_occurred_at"] == _ISO_NOW
    assert actual["last_marker_occurred_at"] == _ISO_NOW


def _validate_self_refinement_c2(case: dict[str, Any], actual: Any) -> None:
    name = case["name"]
    sn = case["stage_name"]
    assert actual is None, (
        f"C2 case={name!r} stage_name={sn!r}: self_refinement uses "
        f"EXACT equality (``sn != 'self_refinement:policy'`` -> "
        f"continue), NOT ``startswith``. A refactor to prefix matching "
        f"(mirroring agent_evaluator) would silently emit summaries "
        f"for unrelated ``self_refinement:*`` stages. Got: {actual!r}"
    )


def _validate_self_refinement_c3(case: dict[str, Any], actual: Any) -> None:
    name = case["name"]
    meta_variant = case["meta_variant"]
    assert actual is not None, (
        f"C3 case={name!r} meta={meta_variant!r}: KEY DIVERGENCE from "
        f"integrator_gate -- self_refinement EMITS a summary with "
        f"``version=None``, ``description=None`` even when metadata "
        f"is degraded. integrator_gate would SKIP entirely. A refactor "
        f"that unified the two would silently flip the emission policy. "
        f"Got: None"
    )
    assert actual["event_id"] == str(RID2)
    assert actual["stage_name"] == "self_refinement:policy"
    assert actual["attempt"] == 7, (
        f"C3 case={name!r}: ``attempt`` must come from payload (NOT "
        f"metadata) and survive degraded metadata; got {actual['attempt']!r}"
    )
    assert actual["version"] is None, (
        f"C3 case={name!r}: ``version`` must default to None when "
        f"nested ``self_refinement`` dict is missing or non-dict; got "
        f"{actual['version']!r}"
    )
    assert actual["description"] is None, (
        f"C3 case={name!r}: ``description`` must default to None when "
        f"nested ``self_refinement`` dict is missing or non-dict; got "
        f"{actual['description']!r}"
    )
    assert actual["marker_count"] == 1, (
        f"C3 case={name!r}: single matching marker in session; got {actual['marker_count']!r}"
    )
    assert actual["first_marker_occurred_at"] == actual["occurred_at"], (
        f"C3 case={name!r}: first marker timestamp must match sole event"
    )
    assert actual["last_marker_occurred_at"] == actual["occurred_at"], (
        f"C3 case={name!r}: last marker timestamp must match sole event"
    )


def _validate_self_refinement_c2_markers(case: dict[str, Any], actual: Any) -> None:
    assert actual is not None
    assert actual["marker_count"] == 2
    assert actual["first_marker_occurred_at"] == _ISO_NOW
    assert actual["last_marker_occurred_at"] == _ISO_LATER
    assert actual["occurred_at"] == _ISO_LATER


def _validate_run_escalated_c4(case: dict[str, Any], actual: Any) -> None:
    assert actual is not None
    assert set(actual.keys()) == RUN_ESCALATED_EXPECTED_KEYS, (
        f"C4: emitted summary must have exactly 6 keys (payload-only -- "
        f"no metadata extraction); got {set(actual.keys())!r}"
    )
    assert actual["event_id"] == str(RID3)
    assert actual["occurred_at"] == _ISO_LATER
    assert actual["actor_id"] == "human:ops"
    assert actual["reason_code"] == "cumulative_stage_failures"
    assert actual["policy_snapshot_id"] == "snap-1"
    assert actual["notes"] == "literal note from operator"


def _validate_run_escalated_c5(case: dict[str, Any], actual: Any) -> None:
    name = case["name"]
    assert actual is not None, (
        f"C5 case={name!r}: KEY DIVERGENCE from integrator_gate -- "
        f"run_escalated has NO metadata guard and emits ANY event "
        f"with the right event_type, even on bad payload. Got: None"
    )
    assert actual["event_id"] == str(RID4)
    assert actual["actor_id"] is None, (
        f"C5 case={name!r}: ``actor_id`` defaults to None via the "
        f"``pl = {{}} if not isinstance(payload, dict) else payload`` "
        f"coercion at runs.py:146; got {actual['actor_id']!r}"
    )
    assert actual["reason_code"] is None
    assert actual["policy_snapshot_id"] is None
    assert actual["notes"] is None


def _validate_security_d1(case: dict[str, Any], actual: bool) -> None:
    name = case["name"]
    value = case["value"]
    assert actual is False, (
        f"D1 case={name!r} value={value!r}: non-dict inputs must "
        f"return ``False`` via the ``isinstance(meta, dict)`` early-out. "
        f"A refactor that dropped the guard would crash on ``in`` "
        f"with non-iterable inputs (int, bool); for iterables it "
        f"would silently emit ``True``/``False`` based on membership "
        f"semantics that vary by type (list vs tuple)."
    )


def _validate_security_d2(case: dict[str, Any], actual: bool) -> None:
    name = case["name"]
    meta_variant = case["meta_variant"]
    expected = case["expected"]
    assert actual is expected, (
        f"D2 case={name!r} meta={meta_variant!r}: KEY DIVERGENCE -- "
        f"membership-OR semantics, NOT value-AND. The exit_only_zero / "
        f"snippet_only_empty_str / exit_none_value cases all pin that "
        f"``key in meta`` is membership (NOT ``meta.get(key)`` "
        f"truthiness). A refactor to truthiness would mark a "
        f"successful zero-exit scan as missing metadata. "
        f"Expected {expected!r}, got {actual!r}"
    )


def _validate_security_d3_wrong_type(case: dict[str, Any], actual: Any) -> None:
    assert actual is None, (
        "D3 step-1: event_type filter precedes guard; a ``stage.started`` "
        "event with full scan metadata must return ``None``"
    )


def _validate_security_d3_no_meta(case: dict[str, Any], actual: Any) -> None:
    assert actual is None, (
        "D3 step-2: ``finding.created`` event without either scan key in "
        "metadata must return ``None`` via the ``_finding_has_security_scan_metadata`` "
        "guard. Pins the two-stage filter (type first, then guard)."
    )


def _validate_security_d4(case: dict[str, Any], actual: Any) -> None:
    assert actual is not None
    assert set(actual.keys()) == SECURITY_SCAN_EXPECTED_KEYS, (
        f"D4: emitted summary must have exactly 10 keys; got {set(actual.keys())!r}"
    )
    assert actual["event_id"] == str(RID3)
    assert actual["occurred_at"] == _ISO_NOW
    assert actual["finding_id"] == "f-1"
    assert actual["category"] == "security"
    assert actual["severity"] == "high"
    assert actual["source_artifact"] == "src/app.py"
    assert actual["security_scan_exit"] == 1
    assert actual["security_scan_ruff_exit"] == 1
    assert actual["security_scan_bandit_exit"] == 0
    assert actual["security_scan_snippet"] == "CVE-2024-12345 detected in dependency\n"


def _validate_security_d5(case: dict[str, Any], actual: Any) -> None:
    assert actual is not None
    assert actual["event_id"] == str(RID2), (
        "D5: latest-wins -- the LAST scan-bearing finding must win. The "
        "interleaved finding WITHOUT scan keys must be silently skipped "
        "(NOT overwrite the first match with null fields)."
    )
    assert actual["finding_id"] == "f-2"
    assert actual["security_scan_exit"] == 0
    assert actual["security_scan_ruff_exit"] == 0
    assert actual["security_scan_bandit_exit"] == 0
    assert actual["security_scan_snippet"] == "clean"
    assert actual["source_artifact"] == "src/db.py"


_INTEGRATOR_NON_MATCHING_EVENTS = [
    stage_started_event(event_id=RID1, payload={"stage_name": "plan:initial"}),
    {"event_type": EVENT_TYPE_RUN_CREATED, "event_id": str(RID2)},
    finding_created_event(event_id=RID3, metadata={}, payload={}),
    run_escalated_event(event_id=RID4, payload={}),
]

_INTEGRATOR_HAPPY_EVENTS = [
    gate_decision_event(
        event_id=RID1,
        metadata=HAPPY_INTEGRATOR_META,
        payload=HAPPY_INTEGRATOR_PAYLOAD,
        occurred_at=_ISO_NOW,
    ),
]

_SECOND_INTEGRATOR_META = dict(HAPPY_INTEGRATOR_META)
_SECOND_INTEGRATOR_META["bundle_id"] = "search-fts-starter"
_SECOND_INTEGRATOR_META["integrator_score"] = 0.42

_INTEGRATOR_LATEST_WINS_EVENTS = [
    gate_decision_event(
        event_id=RID1,
        metadata=HAPPY_INTEGRATOR_META,
        payload=HAPPY_INTEGRATOR_PAYLOAD,
        occurred_at=_ISO_NOW,
    ),
    stage_started_event(event_id=RID3, payload={"stage_name": "verify"}),
    gate_decision_event(
        event_id=RID2,
        metadata=_SECOND_INTEGRATOR_META,
        payload={
            "stage_name": "bundle_compatibility",
            "verdict": "FAIL",
            "failure_reason_code": "score_below_min",
        },
        occurred_at=_ISO_LATER,
    ),
]

_AGENT_WRONG_TYPE_EVENTS = [
    gate_decision_event(
        event_id=RID1,
        metadata={"integrator_gate": True, "bundle_id": "x"},
        payload={"stage_name": "agent_eval:default", "verdict": "PASS"},
    ),
    finding_created_event(
        event_id=RID2,
        metadata={"security_scan_exit": 0},
        payload={"stage_name": "agent_eval:default"},
    ),
]

_AGENT_LATEST_WINS_EVENTS = [
    stage_started_event(event_id=RID1, payload={"stage_name": "agent_eval:a", "attempt": 1}),
    stage_started_event(event_id=RID2, payload="non-dict-payload-oops"),
    stage_started_event(event_id=RID3, payload={"stage_name": "agent_eval:c", "attempt": 2}),
]

_SR_HAPPY_EVENTS = [
    stage_started_event(
        event_id=RID1, payload=SR_PAYLOAD, metadata=SR_METADATA, occurred_at=_ISO_NOW
    ),
]

_SR_TWO_MARKER_EVENTS = [
    stage_started_event(
        event_id=RID1,
        payload=SR_PAYLOAD,
        metadata=SR_METADATA,
        occurred_at=_ISO_NOW,
    ),
    stage_started_event(
        event_id=RID2,
        payload=SR_PAYLOAD,
        metadata={"self_refinement": {"version": "v3", "description": "last row"}},
        occurred_at=_ISO_LATER,
    ),
]

_ESC_PAYLOAD = {
    "actor_id": "human:ops",
    "reason_code": "cumulative_stage_failures",
    "policy_snapshot_id": "snap-1",
    "notes": "literal note from operator",
}

_ESC_HAPPY_EVENTS = [
    run_escalated_event(event_id=RID3, payload=_ESC_PAYLOAD, occurred_at=_ISO_LATER),
]

_HAPPY_SCAN_EVENTS = [
    finding_created_event(
        event_id=RID3,
        metadata=HAPPY_SCAN_META,
        payload=HAPPY_SCAN_PAYLOAD,
        occurred_at=_ISO_NOW,
    ),
]

_SECOND_SCAN_META = {
    "security_scan_exit": 0,
    "security_scan_ruff_exit": 0,
    "security_scan_bandit_exit": 0,
    "security_scan_snippet": "clean",
}

_SECOND_SCAN_PAYLOAD = {
    "finding_id": "f-2",
    "category": "security",
    "severity": "info",
    "source_artifact": "src/db.py",
}

_SCAN_LATEST_WINS_EVENTS = [
    finding_created_event(
        event_id=RID1,
        metadata=HAPPY_SCAN_META,
        payload=HAPPY_SCAN_PAYLOAD,
        occurred_at=_ISO_NOW,
    ),
    finding_created_event(
        event_id=RID3,
        metadata={"category": "lint", "unrelated": True},
        payload={"finding_id": "f-99", "category": "lint"},
        occurred_at=_ISO_LATER,
    ),
    finding_created_event(
        event_id=RID2,
        metadata=_SECOND_SCAN_META,
        payload=_SECOND_SCAN_PAYLOAD,
        occurred_at=_ISO_LATER,
    ),
]

INTEGRATOR_GATE_DIRECT_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "a1_empty",
        "events": [],
        "fn": integrator_gate_timeline_summary,
        "validate": _validate_integrator_a1,
    },
    {
        "case_id": "a2_non_matching",
        "events": _INTEGRATOR_NON_MATCHING_EVENTS,
        "fn": integrator_gate_timeline_summary,
        "validate": _validate_integrator_a2,
    },
    {
        "case_id": "a4_happy",
        "events": _INTEGRATOR_HAPPY_EVENTS,
        "fn": integrator_gate_timeline_summary,
        "validate": _validate_integrator_a4,
    },
    {
        "case_id": "a5_latest_wins",
        "events": _INTEGRATOR_LATEST_WINS_EVENTS,
        "fn": integrator_gate_timeline_summary,
        "validate": _validate_integrator_a5,
    },
)

INTEGRATOR_GATE_METADATA_SKIP_CASES: tuple[dict[str, Any], ...] = tuple(
    {
        "case_id": f"a3_{name}",
        "name": name,
        "meta_variant": meta_variant,
        "events": [
            gate_decision_event(
                event_id=RID1,
                metadata=meta_variant,
                payload={"stage_name": "bundle_compatibility", "verdict": "PASS"},
            ),
        ],
        "fn": integrator_gate_timeline_summary,
        "validate": _validate_integrator_a3,
    }
    for name, meta_variant in (
        ("none", None),
        ("empty_dict", {}),
        ("integrator_gate_false", {"integrator_gate": False}),
        ("integrator_gate_truthy_int", {"integrator_gate": 1}),
        ("integrator_gate_str_True", {"integrator_gate": "True"}),
        ("integrator_gate_none", {"integrator_gate": None}),
        ("non_dict_str", "not-a-dict"),
        ("non_dict_list", ["integrator_gate", True]),
    )
)

AGENT_EVALUATOR_PERSONA_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "b1_wrong_type",
        "events": _AGENT_WRONG_TYPE_EVENTS,
        "fn": agent_evaluator_timeline_summary,
        "validate": _validate_agent_b1,
    },
    *(
        {
            "case_id": f"b2_{name}",
            "name": name,
            "payload_variant": payload_variant,
            "events": [stage_started_event(event_id=RID1, payload=payload_variant)],
            "fn": agent_evaluator_timeline_summary,
            "validate": _validate_agent_b2,
        }
        for name, payload_variant in (
            ("different_prefix", {"stage_name": "plan:initial", "attempt": 1}),
            ("no_trailing_colon", {"stage_name": "agent_eval", "attempt": 1}),
            ("only_partial_prefix", {"stage_name": "agent_eva:default", "attempt": 1}),
            ("stage_name_non_string_int", {"stage_name": 42, "attempt": 1}),
            ("stage_name_none", {"stage_name": None, "attempt": 1}),
            ("non_dict_payload_str", "oops"),
            ("non_dict_payload_none", None),
            ("non_dict_payload_list", ["agent_eval:default"]),
        )
    ),
    *(
        {
            "case_id": f"b3_{name}",
            "name": name,
            "stage_name": stage_name,
            "expected_persona": expected_persona,
            "events": [
                stage_started_event(
                    event_id=RID1, payload={"stage_name": stage_name, "attempt": 3}
                ),
            ],
            "fn": agent_evaluator_timeline_summary,
            "validate": _validate_agent_b3,
        }
        for name, stage_name, expected_persona in (
            ("simple_lowercase", "agent_eval:default", "default"),
            ("multiword_with_underscore", "agent_eval:backend_engineer", "backend_engineer"),
            ("multi_segment_colons", "agent_eval:foo:bar:baz", "foo:bar:baz"),
            ("single_char", "agent_eval:a", "a"),
            ("uppercase_and_digits", "agent_eval:Ops7", "Ops7"),
        )
    ),
    {
        "case_id": "b4_empty_suffix",
        "events": [
            stage_started_event(
                event_id=RID2, payload={"stage_name": "agent_eval:", "attempt": 0}
            ),
        ],
        "fn": agent_evaluator_timeline_summary,
        "validate": _validate_agent_b4,
    },
    {
        "case_id": "b5_latest_wins",
        "events": _AGENT_LATEST_WINS_EVENTS,
        "fn": agent_evaluator_timeline_summary,
        "validate": _validate_agent_b5,
    },
)

SELF_REFINEMENT_AND_ESCALATED_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "c1_happy",
        "events": _SR_HAPPY_EVENTS,
        "fn": self_refinement_timeline_summary,
        "validate": _validate_self_refinement_c1,
    },
    *(
        {
            "case_id": f"c2_{name}",
            "name": name,
            "stage_name": sn,
            "events": [
                stage_started_event(
                    event_id=RID1,
                    payload={"stage_name": sn, "attempt": 1},
                    metadata=SR_METADATA,
                ),
            ],
            "fn": self_refinement_timeline_summary,
            "validate": _validate_self_refinement_c2,
        }
        for name, sn in (
            ("different_suffix", "self_refinement:other"),
            ("no_colon", "self_refinement"),
            ("trailing_extra_segment", "self_refinement:policy:extra"),
            ("policy_prefix_only", "self_refinement:polic"),
            ("with_trailing_colon", "self_refinement:policy:"),
        )
    ),
    *(
        {
            "case_id": f"c3_{name}",
            "name": name,
            "meta_variant": meta_variant,
            "events": [
                stage_started_event(
                    event_id=RID2,
                    payload={"stage_name": "self_refinement:policy", "attempt": 7},
                    metadata=meta_variant,
                ),
            ],
            "fn": self_refinement_timeline_summary,
            "validate": _validate_self_refinement_c3,
        }
        for name, meta_variant in (
            ("metadata_none", None),
            ("metadata_empty", {}),
            ("metadata_self_refinement_none", {"self_refinement": None}),
            ("metadata_self_refinement_non_dict", {"self_refinement": "not-a-dict"}),
            ("metadata_self_refinement_list", {"self_refinement": ["v1"]}),
            ("metadata_non_dict_str", "garbage"),
        )
    ),
    {
        "case_id": "c2_two_markers",
        "events": _SR_TWO_MARKER_EVENTS,
        "fn": self_refinement_timeline_summary,
        "validate": _validate_self_refinement_c2_markers,
    },
    {
        "case_id": "c4_happy_escalated",
        "events": _ESC_HAPPY_EVENTS,
        "fn": run_escalated_timeline_summary,
        "validate": _validate_run_escalated_c4,
    },
    *(
        {
            "case_id": f"c5_{name}",
            "name": name,
            "events": [run_escalated_event(event_id=RID4, payload=payload_variant)],
            "fn": run_escalated_timeline_summary,
            "validate": _validate_run_escalated_c5,
        }
        for name, payload_variant in (
            ("payload_none", None),
            ("payload_str", "garbage"),
            ("payload_list", ["actor", "reason"]),
            ("payload_int", 42),
        )
    ),
)

SECURITY_SCAN_GUARD_CASES: tuple[dict[str, Any], ...] = tuple(
    {
        "case_id": f"d1_{name}",
        "name": name,
        "value": value,
        "fn": _finding_has_security_scan_metadata,
        "input": value,
        "validate": _validate_security_d1,
    }
    for name, value in (
        ("none", None),
        ("string", "not-a-dict"),
        ("list", ["security_scan_exit"]),
        ("tuple", ("security_scan_exit", 0)),
        ("int", 42),
        ("zero", 0),
        ("true", True),
        ("false", False),
    )
) + tuple(
    {
        "case_id": f"d2_{name}",
        "name": name,
        "meta_variant": meta_variant,
        "expected": expected,
        "fn": _finding_has_security_scan_metadata,
        "input": meta_variant,
        "validate": _validate_security_d2,
    }
    for name, meta_variant, expected in (
        ("empty_dict", {}, False),
        ("unrelated_keys_only", {"unrelated": "x", "other": 1}, False),
        ("exit_only_zero", {"security_scan_exit": 0}, True),
        ("exit_only_non_zero", {"security_scan_exit": 1}, True),
        ("snippet_only", {"security_scan_snippet": "ok"}, True),
        ("snippet_only_empty_str", {"security_scan_snippet": ""}, True),
        ("both_keys", {"security_scan_exit": 0, "security_scan_snippet": "ok"}, True),
        ("exit_none_value", {"security_scan_exit": None}, True),
        ("snippet_none_value", {"security_scan_snippet": None}, True),
    )
) + (
    {
        "case_id": "d3_wrong_type",
        "events": [
            stage_started_event(
                event_id=RID1,
                payload={"stage_name": "verify"},
                metadata={
                    "security_scan_exit": 0,
                    "security_scan_snippet": "fake",
                },
            ),
        ],
        "fn": security_scan_on_verify_timeline_summary,
        "validate": _validate_security_d3_wrong_type,
    },
    {
        "case_id": "d3_no_scan_meta",
        "events": [
            finding_created_event(
                event_id=RID2,
                metadata={"category": "lint", "unrelated": True},
                payload={"finding_id": "f-99", "category": "lint", "severity": "low"},
            ),
        ],
        "fn": security_scan_on_verify_timeline_summary,
        "validate": _validate_security_d3_no_meta,
    },
    {
        "case_id": "d4_happy",
        "events": _HAPPY_SCAN_EVENTS,
        "fn": security_scan_on_verify_timeline_summary,
        "validate": _validate_security_d4,
    },
    {
        "case_id": "d5_latest_wins",
        "events": _SCAN_LATEST_WINS_EVENTS,
        "fn": security_scan_on_verify_timeline_summary,
        "validate": _validate_security_d5,
    },
)


def invoke_timeline_summary_case(case: dict[str, Any]) -> Any:
    fn = case["fn"]
    if "events" in case:
        return fn(case["events"])
    return fn(case["input"])
