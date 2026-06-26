from __future__ import annotations

import pytest

from nimbusware_env import find_repo_root

pytestmark = pytest.mark.slow


import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    EventType,
    GateDecisionEmittedEvent,
    GateDecisionEmittedPayload,
    Severity,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from nimbusware_orchestrator.critique_routing import (
    load_critique_router,
    taxonomy_keys_for_run_lifecycle,
)
from nimbusware_orchestrator.llm_plan import (
    IMPLEMENTATION_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_orchestrator.workflow_universal_critique import (
    effective_universal_critique,
    parse_universal_critique_workflow_block,
)

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_taxonomy_keys_for_run_lifecycle_includes_registry_producers_and_critics() -> None:
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    router = load_critique_router(ROOT)
    keys = taxonomy_keys_for_run_lifecycle(reg, router)
    assert "planner" in keys
    assert "backend_writer" in keys
    assert "test_writer" in keys
    assert "product_reference_critic" in keys
    assert "domain_critic" in keys


def test_plan_stub_emits_verdicts_for_yaml_planner_critics() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    orch._execute_plan_stage_stub(rid)
    pr = orch._registry.resolve("product_reference_critic")
    dc = orch._registry.resolve("domain_critic")
    actor_roles: set[UUID] = set()
    for row in mem.list_run_events(str(rid)):
        if row.get("event_type") != "critic.verdict.emitted":
            continue
        raw = row.get("actor_role")
        if raw is not None:
            actor_roles.add(UUID(str(raw)))
    assert actor_roles == {pr, dc}


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_stage_failed_emitted_when_last_impl_critique_gate_is_fail() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="implementation.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_implementation_critique_gate_fail(rid)
    rows = mem.list_run_events(str(rid))
    fails = [
        r
        for r in rows
        if r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "implementation_critique_gate_fail"
    ]
    assert len(fails) == 1


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_stage_failed_dedupes_second_call() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="implementation.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_implementation_critique_gate_fail(rid)
    orch._maybe_emit_stage_failed_for_implementation_critique_gate_fail(rid)
    rows = mem.list_run_events(str(rid))
    fails = [
        r
        for r in rows
        if r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "implementation_critique_gate_fail"
    ]
    assert len(fails) == 1


def test_stage_failed_not_emitted_without_env_on_gate_fail() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="implementation.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_implementation_critique_gate_fail(rid)
    assert not any(r.get("event_type") == "stage.failed" for r in mem.list_run_events(str(rid)))


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_stage_failed_emitted_when_last_test_writer_critique_gate_is_fail() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="test_writer.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_test_writer_critique_gate_fail(rid)
    rows = mem.list_run_events(str(rid))
    fails = [
        r
        for r in rows
        if r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "test_writer_critique_gate_fail"
    ]
    assert len(fails) == 1


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_test_writer_stage_failed_dedupes_second_call() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="test_writer.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_test_writer_critique_gate_fail(rid)
    orch._maybe_emit_stage_failed_for_test_writer_critique_gate_fail(rid)
    rows = mem.list_run_events(str(rid))
    fails = [
        r
        for r in rows
        if r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "test_writer_critique_gate_fail"
    ]
    assert len(fails) == 1


def test_parse_universal_critique_stub_on_workflow() -> None:
    b = parse_universal_critique_workflow_block(ROOT, "universal_critique_stub_on")
    assert b.impl_stub is True
    assert b.tw_enabled is True and b.tw_stub is True
    assert b.pll_enabled is True and b.pll_stub is True
    assert b.fw_enabled is True and b.fw_stub is True
    assert b.mi_enabled is True and b.mi_stub is True
    assert b.impl_llm is False


def test_parse_universal_critique_default_profile_all_off() -> None:
    b = parse_universal_critique_workflow_block(ROOT, "default")
    assert (
        b.impl_stub is False
        and b.tw_enabled is False
        and b.pll_enabled is False
        and b.fw_enabled is False
        and b.mi_enabled is False
    )


def test_impl_stage_failed_emitted_from_workflow_profile_without_env() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("universal_critique_stage_failed_on")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="implementation.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_implementation_critique_gate_fail(rid)
    rows = mem.list_run_events(str(rid))
    assert any(
        r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "implementation_critique_gate_fail"
        for r in rows
    )


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL": "0"},
    clear=False,
)
def test_impl_stage_failed_env_overrides_workflow_true() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("universal_critique_stage_failed_on")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="implementation.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_implementation_critique_gate_fail(rid)
    rows = mem.list_run_events(str(rid))
    assert not any(
        r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "implementation_critique_gate_fail"
        for r in rows
    )


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_stage_failed_emitted_when_last_planner_critique_gate_is_fail() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="planner.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_planner_critique_gate_fail(rid)
    rows = mem.list_run_events(str(rid))
    fails = [
        r
        for r in rows
        if r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "planner_critique_gate_fail"
    ]
    assert len(fails) == 1


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_planner_stage_failed_dedupes_second_call() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="planner.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_planner_critique_gate_fail(rid)
    orch._maybe_emit_stage_failed_for_planner_critique_gate_fail(rid)
    rows = mem.list_run_events(str(rid))
    fails = [
        r
        for r in rows
        if r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "planner_critique_gate_fail"
    ]
    assert len(fails) == 1


def test_planner_stage_failed_not_emitted_without_env_on_gate_fail() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="planner.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_planner_critique_gate_fail(rid)
    assert not any(r.get("event_type") == "stage.failed" for r in mem.list_run_events(str(rid)))


def test_test_writer_stage_failed_not_emitted_without_env_on_gate_fail() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    mem.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name="test_writer.critique",
                verdict=Verdict.FAIL,
                failure_reason_code="llm_gate_fail",
            ),
        ),
    )
    orch._maybe_emit_stage_failed_for_test_writer_critique_gate_fail(rid)
    assert not any(r.get("event_type") == "stage.failed" for r in mem.list_run_events(str(rid)))


def emit_stub_implementation_critique_panel_fail(
    store: object,
    registry: RoleRegistry,
    critique_router: object,
    *,
    run_id: UUID,
) -> None:
    """Same panel shape as ``emit_stub_implementation_critique_panel`` with gate FAIL."""
    owner = registry.resolve("backend_writer")
    tax_keys = critique_router.pairing_for("backend_writer")
    if len(tax_keys) < 2:
        return
    stage_name = IMPLEMENTATION_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        store.append(
            CriticVerdictEmittedEvent(
                event_type=EventType.CRITIC_VERDICT_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=critic_role,
                payload=CriticVerdictEmittedPayload(
                    critic_role=critic_role,
                    verdict=Verdict.PASS,
                    severity=Severity.LOW,
                    owner_role=owner,
                    is_in_domain=True,
                    evidence_refs=["stub://implementation"],
                ),
            ),
        )
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name=stage_name,
                verdict=Verdict.FAIL,
                unanimous_pass_required=True,
                failure_reason_code="stub_gate_fail_test",
            ),
        ),
    )


def emit_stub_test_writer_critique_panel_fail(
    store: object,
    registry: RoleRegistry,
    critique_router: object,
    *,
    run_id: UUID,
) -> None:
    """Same shape as ``emit_stub_test_writer_critique_panel`` with gate FAIL."""
    owner = registry.resolve("test_writer")
    tax_keys = critique_router.pairing_for("test_writer")
    if len(tax_keys) < 2:
        return
    stage_name = TEST_WRITER_CRITIQUE_STAGE
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    for tax_key in tax_keys:
        critic_role = registry.resolve(tax_key)
        store.append(
            CriticVerdictEmittedEvent(
                event_type=EventType.CRITIC_VERDICT_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=critic_role,
                payload=CriticVerdictEmittedPayload(
                    critic_role=critic_role,
                    verdict=Verdict.PASS,
                    severity=Severity.LOW,
                    owner_role=owner,
                    is_in_domain=True,
                    evidence_refs=["stub://test_writer"],
                ),
            ),
        )
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name=stage_name,
                verdict=Verdict.FAIL,
                unanimous_pass_required=True,
                failure_reason_code="stub_gate_fail_test_tw",
            ),
        ),
    )


def _append_impl_gate_fail(orch: object, rid: UUID) -> None:
    store = orch._store
    bw = orch._registry.resolve("backend_writer")
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name=IMPLEMENTATION_CRITIQUE_STAGE,
                verdict=Verdict.FAIL,
                unanimous_pass_required=True,
                failing_critics=[bw],
            ),
        ),
    )


def _append_stage_gate(
    orch: object,
    rid: UUID,
    stage_name: str,
    verdict: Verdict,
    *,
    failure_reason_code: str | None = None,
) -> None:
    """Append a ``gate.decision.emitted`` for ``stage_name`` with the given verdict.

    Used by PASS-suppression / TW + planner emit-finding tests to mirror the impl
    gate-fail helper without redeclaring the same boilerplate per stage.
    """
    store = orch._store
    store.append(
        GateDecisionEmittedEvent(
            event_type=EventType.GATE_DECISION_EMITTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=GateDecisionEmittedPayload(
                stage_name=stage_name,
                verdict=verdict,
                failure_reason_code=failure_reason_code,
            ),
        ),
    )


def test_critique_gate_fail_finding_not_emitted_by_default() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_impl_gate_fail(orch, rid)
    eff = effective_universal_critique(ROOT, "default")
    orch._maybe_emit_critique_gate_fail_findings(rid, eff)
    assert not any(r.get("event_type") == "finding.created" for r in mem.list_run_events(str(rid)))


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_critique_gate_fail_finding_emitted_once_when_enabled() -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_impl_gate_fail(orch, rid)
    eff = effective_universal_critique(ROOT, "default")
    orch._maybe_emit_critique_gate_fail_findings(rid, eff)
    orch._maybe_emit_critique_gate_fail_findings(rid, eff)
    findings = [
        r for r in mem.list_run_events(str(rid)) if r.get("event_type") == "finding.created"
    ]
    assert len(findings) == 1
    meta = findings[0].get("metadata") or {}
    assert meta.get("critique_gate_fail_finding") is True
    assert meta.get("stage_name") == IMPLEMENTATION_CRITIQUE_STAGE
    pl = findings[0].get("payload") or {}
    assert (pl.get("category") or "").lower() == "critique"
    assert "critique_gate:" in str(pl.get("source_artifact"))


def test_emit_finding_env_overrides_yaml_off() -> None:
    """Non-truthy env disables emit even when workflow profile enables YAML."""
    import os
    from unittest.mock import patch

    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("universal_critique_emit_finding_on_gate_fail")
    _append_impl_gate_fail(orch, rid)
    with patch.dict(
        os.environ,
        {"NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL": "0"},
        clear=False,
    ):
        eff = effective_universal_critique(
            ROOT,
            "universal_critique_emit_finding_on_gate_fail",
        )
    orch._maybe_emit_critique_gate_fail_findings(rid, eff)
    assert not any(r.get("event_type") == "finding.created" for r in mem.list_run_events(str(rid)))


def test_universal_critique_router_unknown_producer_falls_back_to_default_critics() -> None:
    router = load_critique_router(ROOT)
    assert router.pairing_for("nonexistent_role_taxonomy_key_xyz") == [
        "product_reference_critic",
        "domain_critic",
    ]


def test_universal_critique_router_pairing_is_case_insensitive() -> None:
    router = load_critique_router(ROOT)
    expected = router.pairing_for("backend_writer")
    assert router.pairing_for("BACKEND_WRITER") == expected
    assert router.pairing_for("  Backend_Writer  ") == expected


def test_universal_critique_router_from_yaml_without_pairings_returns_empty(
    tmp_path: Path,
) -> None:
    from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter

    p = tmp_path / "critique_pairings.yaml"
    p.write_text("version: 1\n", encoding="utf-8")
    router = UniversalCritiqueRouter.from_yaml(p)
    assert router.known_producer_keys() == frozenset()
    assert router.pairing_for("backend_writer") == [
        "product_reference_critic",
        "domain_critic",
    ]


def test_taxonomy_keys_for_run_lifecycle_is_sorted_and_unique() -> None:
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    router = load_critique_router(ROOT)
    keys = taxonomy_keys_for_run_lifecycle(reg, router)
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys))


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_impl_stage_failed_not_emitted_when_last_gate_passes() -> None:
    """Flag on + last gate verdict PASS must not emit ``stage.failed`` (negative branch)."""
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_stage_gate(orch, rid, IMPLEMENTATION_CRITIQUE_STAGE, Verdict.PASS)
    orch._maybe_emit_stage_failed_for_implementation_critique_gate_fail(rid)
    assert not any(
        r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "implementation_critique_gate_fail"
        for r in mem.list_run_events(str(rid))
    )


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_test_writer_stage_failed_not_emitted_when_last_gate_passes() -> None:
    """Flag on + last test-writer gate verdict PASS must not emit ``stage.failed``."""
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_stage_gate(orch, rid, TEST_WRITER_CRITIQUE_STAGE, Verdict.PASS)
    orch._maybe_emit_stage_failed_for_test_writer_critique_gate_fail(rid)
    assert not any(
        r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "test_writer_critique_gate_fail"
        for r in mem.list_run_events(str(rid))
    )


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_planner_stage_failed_not_emitted_when_last_gate_passes() -> None:
    """Flag on + last planner gate verdict PASS must not emit ``stage.failed``."""
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_stage_gate(orch, rid, PLANNER_CRITIQUE_STAGE, Verdict.PASS)
    orch._maybe_emit_stage_failed_for_planner_critique_gate_fail(rid)
    assert not any(
        r.get("event_type") == "stage.failed"
        and (r.get("payload") or {}).get("reason_code") == "planner_critique_gate_fail"
        for r in mem.list_run_events(str(rid))
    )


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_critique_gate_fail_finding_emitted_for_test_writer_stage_when_enabled() -> None:
    """``_maybe_emit_critique_gate_fail_findings`` covers the ``test_writer`` loop arm."""
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_stage_gate(
        orch,
        rid,
        TEST_WRITER_CRITIQUE_STAGE,
        Verdict.FAIL,
        failure_reason_code="llm_gate_fail",
    )
    eff = effective_universal_critique(ROOT, "default")
    orch._maybe_emit_critique_gate_fail_findings(rid, eff)
    findings = [
        r for r in mem.list_run_events(str(rid)) if r.get("event_type") == "finding.created"
    ]
    assert len(findings) == 1
    meta = findings[0].get("metadata") or {}
    assert meta.get("critique_gate_fail_finding") is True
    assert meta.get("stage_name") == TEST_WRITER_CRITIQUE_STAGE


@patch.dict(
    os.environ,
    {"NIMBUSWARE_UNIVERSAL_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL": "1"},
    clear=False,
)
def test_critique_gate_fail_finding_emitted_for_planner_stage_when_enabled() -> None:
    """``_maybe_emit_critique_gate_fail_findings`` covers the ``planner`` loop arm."""
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    _append_stage_gate(
        orch,
        rid,
        PLANNER_CRITIQUE_STAGE,
        Verdict.FAIL,
        failure_reason_code="llm_gate_fail",
    )
    eff = effective_universal_critique(ROOT, "default")
    orch._maybe_emit_critique_gate_fail_findings(rid, eff)
    findings = [
        r for r in mem.list_run_events(str(rid)) if r.get("event_type") == "finding.created"
    ]
    assert len(findings) == 1
    meta = findings[0].get("metadata") or {}
    assert meta.get("critique_gate_fail_finding") is True
    assert meta.get("stage_name") == PLANNER_CRITIQUE_STAGE


def test_universal_critique_router_from_yaml_ignores_non_string_keys(
    tmp_path: Path,
) -> None:
    """Pin §14 #16 silent-skip: non-string ``pairings`` keys are dropped.

    The ``from_yaml`` loop in :class:`UniversalCritiqueRouter` only copies entries whose key
    is a ``str`` and whose value is a ``list``. Integer YAML keys (e.g. ``1: [...]``) survive
    parsing as ``int`` and must be silently ignored so the loaded router still works against
    its taxonomy contract. A valid string-keyed entry alongside the bogus one proves the
    drop is selective (not a whole-file abort).
    """
    from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter

    p = tmp_path / "critique_pairings.yaml"
    p.write_text(
        "pairings:\n  1: [pc, dc]\n  backend_writer: [product_reference_critic, domain_critic]\n",
        encoding="utf-8",
    )
    router = UniversalCritiqueRouter.from_yaml(p)
    assert router.known_producer_keys() == frozenset({"backend_writer"})
    assert router.pairing_for("backend_writer") == [
        "product_reference_critic",
        "domain_critic",
    ]
    assert router.pairing_for("1") == [
        "product_reference_critic",
        "domain_critic",
    ]


def test_universal_critique_router_from_yaml_ignores_non_list_values(
    tmp_path: Path,
) -> None:
    """Pin §14 #16 silent-skip: non-list ``pairings`` values are dropped.

    Mirrors the non-string-key test for the other half of the ``isinstance(k, str) and
    isinstance(v, list)`` guard. An accidental scalar string (``backend_writer: "not_a_list"``)
    must be ignored while a valid sibling entry is preserved, so a typo in one row cannot
    silently corrupt every other pairing in the same YAML.
    """
    from nimbusware_extensions.extension_runtime import UniversalCritiqueRouter

    p = tmp_path / "critique_pairings.yaml"
    p.write_text(
        'pairings:\n  planner: [planner_critic_a]\n  backend_writer: "not_a_list"\n',
        encoding="utf-8",
    )
    router = UniversalCritiqueRouter.from_yaml(p)
    assert router.known_producer_keys() == frozenset({"planner"})
    assert router.pairing_for("planner") == ["planner_critic_a"]
    assert router.pairing_for("backend_writer") == [
        "product_reference_critic",
        "domain_critic",
    ]
