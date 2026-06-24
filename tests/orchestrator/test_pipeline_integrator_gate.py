from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from agent_core.models import (
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    Severity,
    Verdict,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator


def _has_integrator_gate_event(events: list[dict[str, Any]]) -> bool:
    """Return True iff ``events`` contains a ``gate.decision.emitted`` row.

    Factors out the recurring presence check used by the follow-on 64 env-layer
    string-arm contract tests below. The five pre-existing gate tests keep
    their inline assertions (which inspect richer metadata / verdict / score
    details that this helper does not return) to avoid mixing a behavioral
    slice with refactor noise outside follow-on 64's scope.
    """
    return any(r["event_type"] == EventType.GATE_DECISION_EMITTED.value for r in events)


def test_emit_integrator_gate_when_yaml_enabled_via_monkeypatch() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    with patch(
        "nimbusware_orchestrator.integrator_gate.load_integrator_gate_emit_enabled",
        return_value=True,
    ):
        orch._emit_bundle_integrator_gate(rid)  # noqa: SLF001
    types = [r["event_type"] for r in mem.list_run_events(str(rid))]
    assert EventType.GATE_DECISION_EMITTED.value in types


def test_emit_integrator_gate_includes_score_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raising=False)
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("integrator_gate_on")
    with patch(
        "nimbusware_orchestrator.integrator_gate.load_integrator_gate_emit_enabled",
        return_value=False,
    ):
        orch._emit_bundle_integrator_gate(rid)  # noqa: SLF001
    gate_rows = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.GATE_DECISION_EMITTED.value
    ]
    assert len(gate_rows) == 1
    meta = gate_rows[0].get("metadata") or {}
    assert meta.get("integrator_gate") is True
    assert meta.get("bundle_id") == "auth-rbac-starter"
    assert meta.get("bundle_title") == "Admin RBAC starter"
    assert meta.get("integrator_score") == 1.0
    assert meta.get("min_score_to_pass") == pytest.approx(0.7)
    assert meta.get("integrator_project_tags") == ["auth", "rbac"]
    assert meta.get("integrator_bundle_tags") == ["auth", "rbac"]
    assert meta.get("integrator_matched_tags") == ["auth", "rbac"]
    ranking = meta.get("bundle_compatibility_ranking")
    assert isinstance(ranking, list) and len(ranking) >= 1
    assert meta.get("bundle_compatibility_ranking_count") == len(ranking)
    assert meta.get("selected_bundle_rank") is not None
    assert ranking[meta["selected_bundle_rank"]]["bundle_id"] == "auth-rbac-starter"
    verdict = (gate_rows[0].get("payload") or {}).get("verdict")
    assert verdict == Verdict.PASS or verdict == "PASS"


def test_emit_integrator_gate_fail_when_workflow_project_tags_mismatch_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raising=False)
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("integrator_gate_mismatch")
    with patch(
        "nimbusware_orchestrator.integrator_gate.load_integrator_gate_emit_enabled",
        return_value=False,
    ):
        orch._emit_bundle_integrator_gate(rid)  # noqa: SLF001
    gate_rows = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.GATE_DECISION_EMITTED.value
    ]
    assert len(gate_rows) == 1
    verdict = (gate_rows[0].get("payload") or {}).get("verdict")
    assert verdict == Verdict.FAIL or verdict == "FAIL"
    meta = gate_rows[0].get("metadata") or {}
    assert meta.get("integrator_score") == 0.0
    assert meta.get("integrator_matched_tags") == []
    assert meta.get("integrator_project_tags") == ["billing", "stripe"]


def test_emit_integrator_gate_env_min_score_overrides_threshold_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raising=False)
    monkeypatch.setenv("NIMBUSWARE_INTEGRATOR_MIN_SCORE_TO_PASS", "0.99")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("integrator_gate_on")
    with patch(
        "nimbusware_orchestrator.integrator_gate.load_integrator_gate_emit_enabled",
        return_value=False,
    ):
        orch._emit_bundle_integrator_gate(rid)  # noqa: SLF001
    meta = next(
        r.get("metadata") or {}
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.GATE_DECISION_EMITTED.value
    )
    assert meta.get("min_score_to_pass") == pytest.approx(0.99)
    assert meta.get("integrator_score") == 1.0


def test_emit_integrator_gate_when_workflow_profile_enables_integrator_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raising=False)
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("integrator_gate_on")
    with patch(
        "nimbusware_orchestrator.integrator_gate.load_integrator_gate_emit_enabled",
        return_value=False,
    ):
        orch._emit_bundle_integrator_gate(rid)  # noqa: SLF001
    types = [r["event_type"] for r in mem.list_run_events(str(rid))]
    assert EventType.GATE_DECISION_EMITTED.value in types


def test_emit_integrator_gate_env_force_on_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #13 env force-on tuple ``.strip().lower() in ("1", "true", "yes")``.

    :meth:`RunOrchestrator._emit_bundle_integrator_gate` consults
    ``NIMBUSWARE_EMIT_INTEGRATOR_GATE`` *before* the workflow / thresholds-YAML
    OR-gate. Existing tests in this module never set the env to a non-empty
    value — every prior test starts with
    ``monkeypatch.delenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raising=False)`` — so
    the full env-layer string-arm surface is unpinned. This test exhaustively
    pins the case-folded + whitespace-trimmed variants of the force-on tuple.

    Workflow profile is ``default`` (``integrator_gate.enabled: false`` in
    [`configs/workflows/default.yaml`](configs\\workflows\\default.yaml))
    AND ``load_integrator_gate_emit_enabled`` is patched to ``False`` so any
    emitted ``gate.decision.emitted`` event comes only from the env force-on
    branch. The existing ``configs/integrator/thresholds.yaml`` is required
    to be present (it is) — the function returns early without one.

    Closes the env-layer trilogy started in follow-on 62
    (:func:`security_scan_metadata_on_verify_enabled`) and follow-on 63
    (:meth:`_maybe_emit_agent_evaluator_stage`). Per-case ``force_on
    raw=<raw>`` message identifies the failing env scalar.
    """
    cases: list[tuple[str, str]] = [
        ("canon_one", "1"),
        ("canon_true", "true"),
        ("canon_yes", "yes"),
        ("upper_true", "TRUE"),
        ("title_true", "True"),
        ("upper_yes", "YES"),
        ("title_yes", "Yes"),
        ("mixed_true", "trUE"),
        ("mixed_yes", "yEs"),
        ("ws_one_pad", "  1  "),
        ("ws_true_pad", " true "),
        ("ws_tab_yes_lf", "\tyes\n"),
        ("ws_upper_true_pad", "  TRUE  "),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raw)
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("default")
        with patch(
            "nimbusware_orchestrator.integrator_gate.load_integrator_gate_emit_enabled",
            return_value=False,
        ):
            orch._emit_bundle_integrator_gate(rid)  # noqa: SLF001
        assert _has_integrator_gate_event(mem.list_run_events(str(rid))), f"force_on raw={raw!r}"


def test_emit_integrator_gate_env_kill_switch_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #13 env kill-switch tuple ``.strip().lower() in ("0", "false", "no")``.

    Mirror of the force-on contract for the falsy tuple. Workflow profile is
    ``integrator_gate_on`` (``integrator_gate.enabled: true``) AND
    ``load_integrator_gate_emit_enabled`` is patched to ``False`` so without
    the env kill-switch the workflow alone would emit. Asserting NO
    ``gate.decision.emitted`` per case isolates the env kill-switch branch.

    The kill-switch returns **before** the workflow OR-gate check
    (``yaml_on or wf_on``), so workflow-on cannot rescue it — pinning this
    contract prevents a future refactor from accidentally moving the
    kill-switch below the OR-gate. Per-case ``kill_switch raw=<raw>`` message
    identifies the failing env scalar.
    """
    cases: list[tuple[str, str]] = [
        ("canon_zero", "0"),
        ("canon_false", "false"),
        ("canon_no", "no"),
        ("upper_false", "FALSE"),
        ("title_false", "False"),
        ("upper_no", "NO"),
        ("title_no", "No"),
        ("mixed_false", "fAlSe"),
        ("mixed_no", "nO"),
        ("ws_zero_pad", "  0  "),
        ("ws_false_pad", " false "),
        ("ws_tab_no_lf", "\tno\n"),
        ("ws_upper_false_pad", "  FALSE  "),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raw)
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("integrator_gate_on")
        orch._emit_bundle_integrator_gate(rid)  # noqa: SLF001
        assert not _has_integrator_gate_event(mem.list_run_events(str(rid))), (
            f"kill_switch raw={raw!r}"
        )


def test_emit_integrator_gate_env_fallthrough_to_yaml_string_arm_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #13 exclusive-tuple-membership: env values not in either tuple fall through.

    Critical asymmetry pinned: the env layer's tuples in
    :meth:`_emit_bundle_integrator_gate` are ``("1", "true", "yes")`` and
    ``("0", "false", "no")`` — they **exclude** ``"on"`` / ``"off"``. So
    ``NIMBUSWARE_EMIT_INTEGRATOR_GATE=on`` falls past both tuples to the workflow
    / thresholds-YAML OR-gate ``yaml_on or wf_on`` rather than forcing-on.
    With ``load_integrator_gate_emit_enabled`` patched to ``False`` the
    OR-gate collapses to ``wf_on`` only, matching the sibling pattern pinned
    by follow-ons 62 / 63.

    Each case asserts against **both** workflow profiles (``default`` → no
    emit, ``integrator_gate_on`` → emit) so the asymmetry surfaces with a
    single per-case message identifying the failing workflow side and the
    offending env scalar. Covers four fallthrough failure modes:

    1. **Asymmetric YAML tokens** (``"on"`` / ``"off"`` / ``"ON"`` / ``"  OFF  "``).
    2. **Stripped-to-empty inputs** (``""`` / ``"   "``).
    3. **Unknown tokens** (``"maybe"`` / ``"true!"``).
    4. **Interior whitespace** (``" ye s "``).

    A future "unify the env tuple with the YAML coercion tuple" refactor
    (adding ``"on"`` / ``"off"`` to the env tuples) would silently flip the
    semantics of ``NIMBUSWARE_EMIT_INTEGRATOR_GATE=on`` from "follow OR-gate" to
    "force on" — this test fails loudly on that change. Closes the env-layer
    trilogy: all three sibling env layers in ``pipeline.py`` now share an
    identical pinned string-arm contract.
    """
    cases: list[tuple[str, str]] = [
        ("fall_on", "on"),
        ("fall_off", "off"),
        ("fall_upper_on", "ON"),
        ("fall_padded_off", "  OFF  "),
        ("fall_empty", ""),
        ("fall_whitespace", "   "),
        ("fall_maybe", "maybe"),
        ("fall_near_miss", "true!"),
        ("fall_interior_ws", " ye s "),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_EMIT_INTEGRATOR_GATE", raw)
        orch_off, mem_off = make_dev_orchestrator()
        rid_off = orch_off.create_run("default")
        with patch(
            "nimbusware_orchestrator.integrator_gate.load_integrator_gate_emit_enabled",
            return_value=False,
        ):
            orch_off._emit_bundle_integrator_gate(rid_off)  # noqa: SLF001
        assert not _has_integrator_gate_event(
            mem_off.list_run_events(str(rid_off)),
        ), f"fall_through workflow=off raw={raw!r}"
        orch_on, mem_on = make_dev_orchestrator()
        rid_on = orch_on.create_run("integrator_gate_on")
        with patch(
            "nimbusware_orchestrator.integrator_gate.load_integrator_gate_emit_enabled",
            return_value=False,
        ):
            orch_on._emit_bundle_integrator_gate(rid_on)  # noqa: SLF001
        assert _has_integrator_gate_event(
            mem_on.list_run_events(str(rid_on)),
        ), f"fall_through workflow=on raw={raw!r}"


def test_notice_escalate_findings_once() -> None:
    with patch(
        "nimbusware_orchestrator._pipeline.escalation.load_notice_escalate_at_cumulative_findings",
        return_value=1,
    ):
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("default")
        writer = orch._registry.resolve("backend_writer")  # noqa: SLF001
        ctx = orch._strictness_context(rid)  # noqa: SLF001
        payload = FindingCreatedPayload.model_validate(
            {
                "finding_id": str(__import__("uuid").uuid4()),
                "category": "test",
                "owner_role": str(writer),
                "severity": Severity.LOW.value,
                "source_artifact": "unit",
                "repro_steps": ["x"],
                "required_fixes": [],
            },
            context=ctx,
        )
        mem.append(
            FindingCreatedEvent(
                event_type=EventType.FINDING_CREATED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=datetime.now(timezone.utc),
                payload=payload,
            ),
        )
        orch._maybe_notice_escalate_findings(rid)  # noqa: SLF001
        esc = [
            r
            for r in mem.list_run_events(str(rid))
            if r["event_type"] == EventType.RUN_ESCALATED.value
            and (r.get("payload") or {}).get("reason_code") == "cumulative_findings_notice"
        ]
        assert len(esc) == 1
        orch._maybe_notice_escalate_findings(rid)  # noqa: SLF001
        esc2 = [
            r
            for r in mem.list_run_events(str(rid))
            if r["event_type"] == EventType.RUN_ESCALATED.value
            and (r.get("payload") or {}).get("reason_code") == "cumulative_findings_notice"
        ]
        assert len(esc2) == 1
